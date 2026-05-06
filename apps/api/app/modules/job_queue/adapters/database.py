from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_queue.adapters.base import JobQueueBackend
from app.modules.job_queue.models import JobQueueDefinition, JobQueueEvent, JobQueueItem
from app.modules.job_queue.repository import JobQueueRepository


class DatabaseJobQueueBackend(JobQueueBackend):
    backend_name = "database"

    def __init__(self, session: AsyncSession) -> None:
        self.repository = JobQueueRepository(session)

    async def upsert_definition(
        self,
        definition: JobQueueDefinition,
    ) -> tuple[JobQueueDefinition, bool]:
        return await self.repository.upsert_definition(definition)

    async def get_definition_by_job_type(self, job_type: str) -> JobQueueDefinition | None:
        return await self.repository.get_definition_by_job_type(job_type)

    async def list_definitions(
        self,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
    ) -> list[JobQueueDefinition]:
        return await self.repository.list_definitions(
            status=status,
            queue_name=queue_name,
            job_type=job_type,
        )

    async def create_job(self, job: JobQueueItem) -> JobQueueItem:
        return await self.repository.create_job(job)

    async def get_job(self, job_id: UUID) -> JobQueueItem | None:
        return await self.repository.get_job(job_id)

    async def get_job_by_idempotency_key(
        self,
        workspace_id: UUID | None,
        idempotency_key: str,
    ) -> JobQueueItem | None:
        return await self.repository.get_job_by_idempotency_key(workspace_id, idempotency_key)

    async def list_jobs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[JobQueueItem]:
        return await self.repository.list_jobs(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            queue_name=queue_name,
            job_type=job_type,
            status=status,
        )

    async def claim_jobs(
        self,
        now: datetime,
        queue_name: str,
        worker_id: str,
        limit: int,
        lock_seconds: int,
    ) -> list[JobQueueItem]:
        return await self.repository.claim_jobs(
            now=now,
            queue_name=queue_name,
            worker_id=worker_id,
            limit=limit,
            lock_seconds=lock_seconds,
        )

    async def update_job(self, job: JobQueueItem) -> JobQueueItem:
        return await self.repository.update_job(job)

    async def add_event(self, event: JobQueueEvent) -> JobQueueEvent:
        return await self.repository.add_event(event)

    async def list_events(self, job_id: UUID) -> list[JobQueueEvent]:
        return await self.repository.list_events(job_id)
