from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_queue.models import JobQueueItem
from app.modules.job_queue.service import JobQueueService


@dataclass(frozen=True)
class JobQueueHandlerResult:
    result_json: dict[str, Any] = field(default_factory=dict)
    completed_with_warnings: bool = False


JobQueueHandler = Callable[[JobQueueItem, AsyncSession], Awaitable[JobQueueHandlerResult]]


class JobQueueDispatcher:
    def __init__(
        self,
        session: AsyncSession,
        service: JobQueueService | None = None,
        handlers: dict[str, JobQueueHandler] | None = None,
    ) -> None:
        self.session = session
        self.service = service or JobQueueService(session)
        self.handlers = handlers or {}

    def register_handler(self, job_type: str, handler: JobQueueHandler) -> None:
        self.handlers[job_type] = handler

    async def dispatch_job(self, job_id: UUID, worker_id: str) -> JobQueueItem:
        job = await self.service.start_job(job_id, worker_id=worker_id, commit=False)
        handler = self.handlers.get(job.job_type)
        if handler is None:
            return await self.service.fail_job(
                job.id,
                "unsupported_job_type",
                f"No handler is registered for job type {job.job_type}",
                commit=True,
            )
        try:
            result = await handler(job, self.session)
        except Exception as error:
            if job.attempts >= job.max_attempts:
                job.error_code = type(error).__name__[:120]
                job.error_message = str(error)[:2000]
                return await self.service.move_to_dead_letter(job.id, commit=True)
            failed = await self.service.fail_job(
                job.id,
                type(error).__name__,
                str(error),
                commit=False,
            )
            failed.status = "running"
            await self.service.retry_job(failed.id, commit=True)
            return failed
        return await self.service.complete_job(
            job.id,
            result.result_json,
            completed_with_warnings=result.completed_with_warnings,
            commit=True,
        )
