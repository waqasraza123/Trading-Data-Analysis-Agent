from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.modules.job_queue.models import JobQueueDefinition, JobQueueEvent, JobQueueItem


class JobQueueBackend(ABC):
    backend_name: str

    @abstractmethod
    async def upsert_definition(
        self,
        definition: JobQueueDefinition,
    ) -> tuple[JobQueueDefinition, bool]:
        raise NotImplementedError

    @abstractmethod
    async def get_definition_by_job_type(self, job_type: str) -> JobQueueDefinition | None:
        raise NotImplementedError

    @abstractmethod
    async def list_definitions(
        self,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
    ) -> list[JobQueueDefinition]:
        raise NotImplementedError

    @abstractmethod
    async def create_job(self, job: JobQueueItem) -> JobQueueItem:
        raise NotImplementedError

    @abstractmethod
    async def get_job(self, job_id: UUID) -> JobQueueItem | None:
        raise NotImplementedError

    @abstractmethod
    async def get_job_by_idempotency_key(
        self,
        workspace_id: UUID | None,
        idempotency_key: str,
    ) -> JobQueueItem | None:
        raise NotImplementedError

    @abstractmethod
    async def list_jobs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[JobQueueItem]:
        raise NotImplementedError

    @abstractmethod
    async def claim_jobs(
        self,
        now: datetime,
        queue_name: str,
        worker_id: str,
        limit: int,
        lock_seconds: int,
    ) -> list[JobQueueItem]:
        raise NotImplementedError

    @abstractmethod
    async def update_job(self, job: JobQueueItem) -> JobQueueItem:
        raise NotImplementedError

    @abstractmethod
    async def add_event(self, event: JobQueueEvent) -> JobQueueEvent:
        raise NotImplementedError

    @abstractmethod
    async def list_events(self, job_id: UUID) -> list[JobQueueEvent]:
        raise NotImplementedError
