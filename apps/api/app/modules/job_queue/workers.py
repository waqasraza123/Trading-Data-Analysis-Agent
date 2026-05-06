import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.modules.job_queue.dispatcher import JobQueueDispatcher
from app.modules.job_queue.service import JobQueueService
from app.modules.runtime_supervisor.heartbeats import RuntimeWorkerHeartbeatClient


class JobQueueWorkerRuntime:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        queue_name: str,
        worker_id: str | None = None,
        logger: logging.Logger | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        max_concurrency: int = 4,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.queue_name = queue_name
        self.worker_id = worker_id or f"job-queue-worker-{queue_name}-{uuid4()}"
        self.logger = logger or logging.getLogger(__name__)
        self.sleep = sleep
        self.max_concurrency = max(1, min(max_concurrency, 50))
        self.stopping = asyncio.Event()
        self.heartbeat = RuntimeWorkerHeartbeatClient(
            session_factory=session_factory,
            settings=settings,
            worker_definition_key="job_queue_worker",
            worker_id=self.worker_id,
        )

    async def run_forever(self) -> None:
        self.logger.info(
            "job_queue_worker_started",
            extra={"worker_id": self.worker_id, "queue_name": self.queue_name},
        )
        await self.heartbeat.starting()
        try:
            while not self.stopping.is_set():
                claimed_count = 0
                try:
                    claimed_count = await self.poll_once()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    self.logger.exception(
                        "job_queue_worker_poll_failed",
                        extra={"worker_id": self.worker_id, "queue_name": self.queue_name},
                    )
                await self.heartbeat.running(
                    {"queueName": self.queue_name, "claimedCount": claimed_count}
                )
                await self.sleep(self.next_sleep_seconds(claimed_count))
        finally:
            await self.heartbeat.stopped()
            self.logger.info(
                "job_queue_worker_stopped",
                extra={"worker_id": self.worker_id, "queue_name": self.queue_name},
            )

    async def poll_once(self) -> int:
        async with self.session_factory() as session:
            service = JobQueueService(session, settings=self.settings)
            jobs = await service.claim_jobs(
                queue_name=self.queue_name,
                worker_id=self.worker_id,
                limit=self.settings.job_queue_claim_batch_size,
            )
            job_ids = [job.id for job in jobs]
        await self.dispatch_jobs(job_ids)
        return len(job_ids)

    async def dispatch_jobs(self, job_ids: list[UUID]) -> None:
        if not job_ids:
            return
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_one(job_id: UUID) -> None:
            async with semaphore, self.session_factory() as session:
                dispatcher = JobQueueDispatcher(session, JobQueueService(session, self.settings))
                await dispatcher.dispatch_job(job_id, self.worker_id)

        await asyncio.gather(*(run_one(job_id) for job_id in job_ids))

    def next_sleep_seconds(self, claimed_count: int) -> float:
        if claimed_count:
            return 0.1
        return 5.0 + random.uniform(0, 2)

    async def stop(self) -> None:
        self.stopping.set()
