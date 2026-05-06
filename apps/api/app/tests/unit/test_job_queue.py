from datetime import datetime, timedelta
from uuid import UUID

import pytest

from app.config import AppEnvironment, Settings
from app.core.time import utc_now
from app.modules.job_queue.adapters.base import JobQueueBackend
from app.modules.job_queue.models import (
    JobQueueDefinition,
    JobQueueEvent,
    JobQueueItem,
    JobQueueItemStatus,
    JobQueueJobType,
)
from app.modules.job_queue.schemas import JobQueueJobCreate
from app.modules.job_queue.service import JobQueueService


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeJobQueueBackend(JobQueueBackend):
    backend_name = "fake"

    def __init__(self) -> None:
        self.definitions: dict[str, JobQueueDefinition] = {}
        self.jobs: dict[UUID, JobQueueItem] = {}
        self.events: list[JobQueueEvent] = []

    async def upsert_definition(
        self,
        definition: JobQueueDefinition,
    ) -> tuple[JobQueueDefinition, bool]:
        created = definition.key not in self.definitions
        self.definitions[definition.key] = definition
        return definition, created

    async def get_definition_by_job_type(self, job_type: str) -> JobQueueDefinition | None:
        for definition in self.definitions.values():
            if definition.job_type == job_type:
                return definition
        return None

    async def list_definitions(
        self,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
    ) -> list[JobQueueDefinition]:
        definitions = list(self.definitions.values())
        if status is not None:
            definitions = [definition for definition in definitions if definition.status == status]
        if queue_name is not None:
            definitions = [
                definition for definition in definitions if definition.queue_name == queue_name
            ]
        if job_type is not None:
            definitions = [
                definition for definition in definitions if definition.job_type == job_type
            ]
        return definitions

    async def create_job(self, job: JobQueueItem) -> JobQueueItem:
        self.jobs[job.id] = job
        return job

    async def get_job(self, job_id: UUID) -> JobQueueItem | None:
        return self.jobs.get(job_id)

    async def get_job_by_idempotency_key(
        self,
        workspace_id: UUID | None,
        idempotency_key: str,
    ) -> JobQueueItem | None:
        for job in self.jobs.values():
            if job.workspace_id == workspace_id and job.idempotency_key == idempotency_key:
                return job
        return None

    async def list_jobs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[JobQueueItem]:
        jobs = list(self.jobs.values())
        if workspace_id is not None:
            jobs = [job for job in jobs if job.workspace_id == workspace_id]
        if queue_name is not None:
            jobs = [job for job in jobs if job.queue_name == queue_name]
        if job_type is not None:
            jobs = [job for job in jobs if job.job_type == job_type]
        if status is not None:
            jobs = [job for job in jobs if job.status == status]
        return jobs[offset : offset + limit]

    async def claim_jobs(
        self,
        now: datetime,
        queue_name: str,
        worker_id: str,
        limit: int,
        lock_seconds: int,
    ) -> list[JobQueueItem]:
        claimed: list[JobQueueItem] = []
        for job in self.jobs.values():
            if len(claimed) >= limit:
                break
            if job.queue_name != queue_name:
                continue
            if job.status not in {
                JobQueueItemStatus.PENDING.value,
                JobQueueItemStatus.SCHEDULED.value,
                JobQueueItemStatus.RETRYING.value,
            }:
                continue
            if job.available_at is not None and job.available_at > now:
                continue
            job.status = JobQueueItemStatus.RUNNING.value
            job.attempts += 1
            job.locked_by = worker_id
            job.locked_until = utc_now() + timedelta(seconds=lock_seconds)
            job.started_at = job.started_at or utc_now()
            claimed.append(job)
        return claimed

    async def update_job(self, job: JobQueueItem) -> JobQueueItem:
        self.jobs[job.id] = job
        return job

    async def add_event(self, event: JobQueueEvent) -> JobQueueEvent:
        self.events.append(event)
        return event

    async def list_events(self, job_id: UUID) -> list[JobQueueEvent]:
        return [event for event in self.events if event.job_id == job_id]


def make_service() -> tuple[JobQueueService, FakeJobQueueBackend]:
    backend = FakeJobQueueBackend()
    service = JobQueueService(
        FakeSession(),
        settings=Settings(_env_file=None, app_env=AppEnvironment.TEST),
        backend=backend,
    )
    return service, backend


@pytest.mark.asyncio
async def test_enqueue_job_uses_default_definition_and_idempotency() -> None:
    service, _ = make_service()

    first = await service.enqueue_job(
        JobQueueJobCreate(
            job_type=JobQueueJobType.READ_MODEL_REBUILD,
            idempotency_key="read-model-1",
            payload_json={"workspaceId": "workspace-1"},
        )
    )
    second = await service.enqueue_job(
        JobQueueJobCreate(
            job_type=JobQueueJobType.READ_MODEL_REBUILD,
            idempotency_key="read-model-1",
            payload_json={"workspaceId": "workspace-1"},
        )
    )

    assert first.id == second.id
    assert first.queue_name == "read_models"
    assert first.status == JobQueueItemStatus.PENDING.value


@pytest.mark.asyncio
async def test_claim_heartbeat_retry_and_dead_letter_transitions() -> None:
    service, _ = make_service()
    job = await service.enqueue_job(
        JobQueueJobCreate(
            job_type=JobQueueJobType.BACKFILL_ITEM,
            payload_json={"targetType": "signal"},
            max_attempts=1,
        )
    )

    claimed = await service.claim_jobs("backfills", "worker-1", limit=1)
    heartbeat = await service.heartbeat(claimed[0].id, "worker-1")

    assert heartbeat.locked_by == "worker-1"
    dead_letter = await service.retry_job(job.id)
    assert dead_letter.status == JobQueueItemStatus.DEAD_LETTER.value


@pytest.mark.asyncio
async def test_cancel_job_records_terminal_status() -> None:
    service, _ = make_service()
    job = await service.enqueue_job(
        JobQueueJobCreate(
            job_type=JobQueueJobType.DATA_QUALITY_RUN,
            payload_json={"scope": "workspace"},
        )
    )

    cancelled = await service.cancel_job(job.id, reason="operator_requested")
    events = await service.list_events(job.id)

    assert cancelled.status == JobQueueItemStatus.CANCELLED.value
    assert events[-1].event_type == "cancelled"


@pytest.mark.asyncio
async def test_seed_default_definitions_is_idempotent() -> None:
    service, _ = make_service()

    first = await service.seed_default_job_definitions()
    second = await service.seed_default_job_definitions()

    assert first.seeded_count == len(JobQueueJobType)
    assert second.updated_count == len(JobQueueJobType)
