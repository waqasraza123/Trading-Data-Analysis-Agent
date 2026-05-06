from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.job_queue.models import (
    JobQueueDefinition,
    JobQueueEvent,
    JobQueueItem,
    JobQueueItemStatus,
    JobQueuePriority,
)


class JobQueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_definition(
        self,
        definition: JobQueueDefinition,
    ) -> tuple[JobQueueDefinition, bool]:
        existing = await self.get_definition_by_key(definition.key)
        if existing is None:
            self.session.add(definition)
            await self.session.flush()
            await self.session.refresh(definition)
            return definition, True
        existing.name = definition.name
        existing.description = definition.description
        existing.status = definition.status
        existing.queue_name = definition.queue_name
        existing.job_type = definition.job_type
        existing.max_attempts = definition.max_attempts
        existing.default_priority = definition.default_priority
        existing.timeout_seconds = definition.timeout_seconds
        existing.metadata_json = definition.metadata_json
        await self.session.flush()
        await self.session.refresh(existing)
        return existing, False

    async def get_definition_by_key(self, key: str) -> JobQueueDefinition | None:
        statement: Select[tuple[JobQueueDefinition]] = select(JobQueueDefinition).where(
            JobQueueDefinition.key == key
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_definition_by_job_type(self, job_type: str) -> JobQueueDefinition | None:
        statement: Select[tuple[JobQueueDefinition]] = (
            select(JobQueueDefinition)
            .where(JobQueueDefinition.job_type == job_type)
            .order_by(JobQueueDefinition.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_definitions(
        self,
        status: str | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
    ) -> list[JobQueueDefinition]:
        statement: Select[tuple[JobQueueDefinition]] = select(JobQueueDefinition).order_by(
            JobQueueDefinition.queue_name.asc(),
            JobQueueDefinition.job_type.asc(),
        )
        if status is not None:
            statement = statement.where(JobQueueDefinition.status == status)
        if queue_name is not None:
            statement = statement.where(JobQueueDefinition.queue_name == queue_name)
        if job_type is not None:
            statement = statement.where(JobQueueDefinition.job_type == job_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_job(self, job: JobQueueItem) -> JobQueueItem:
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: UUID) -> JobQueueItem | None:
        return await self.session.get(JobQueueItem, job_id)

    async def get_job_by_idempotency_key(
        self,
        workspace_id: UUID | None,
        idempotency_key: str,
    ) -> JobQueueItem | None:
        statement: Select[tuple[JobQueueItem]] = select(JobQueueItem).where(
            JobQueueItem.idempotency_key == idempotency_key
        )
        if workspace_id is None:
            statement = statement.where(JobQueueItem.workspace_id.is_(None))
        else:
            statement = statement.where(JobQueueItem.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        queue_name: str | None = None,
        job_type: str | None = None,
        status: str | None = None,
    ) -> list[JobQueueItem]:
        statement: Select[tuple[JobQueueItem]] = (
            select(JobQueueItem)
            .order_by(JobQueueItem.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(JobQueueItem.workspace_id == workspace_id)
        if queue_name is not None:
            statement = statement.where(JobQueueItem.queue_name == queue_name)
        if job_type is not None:
            statement = statement.where(JobQueueItem.job_type == job_type)
        if status is not None:
            statement = statement.where(JobQueueItem.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def claim_jobs(
        self,
        now: datetime,
        queue_name: str,
        worker_id: str,
        limit: int,
        lock_seconds: int,
    ) -> list[JobQueueItem]:
        lock_until = now + timedelta(seconds=lock_seconds)
        priority_order = case(
            (JobQueueItem.priority == JobQueuePriority.URGENT.value, 0),
            (JobQueueItem.priority == JobQueuePriority.HIGH.value, 1),
            (JobQueueItem.priority == JobQueuePriority.NORMAL.value, 2),
            else_=3,
        )
        statement: Select[tuple[JobQueueItem]] = (
            select(JobQueueItem)
            .where(
                JobQueueItem.queue_name == queue_name,
                JobQueueItem.attempts < JobQueueItem.max_attempts,
                or_(JobQueueItem.available_at.is_(None), JobQueueItem.available_at <= now),
                or_(
                    and_(
                        JobQueueItem.status.in_(
                            [
                                JobQueueItemStatus.PENDING.value,
                                JobQueueItemStatus.SCHEDULED.value,
                                JobQueueItemStatus.RETRYING.value,
                            ]
                        ),
                        or_(
                            JobQueueItem.locked_by.is_(None),
                            JobQueueItem.locked_until.is_(None),
                            JobQueueItem.locked_until <= now,
                        ),
                    ),
                    and_(
                        JobQueueItem.status == JobQueueItemStatus.RUNNING.value,
                        JobQueueItem.locked_until.is_not(None),
                        JobQueueItem.locked_until <= now,
                    ),
                ),
            )
            .order_by(priority_order.asc(), JobQueueItem.available_at.asc().nullsfirst())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(statement)
        jobs = list(result.scalars().all())
        for job in jobs:
            job.status = JobQueueItemStatus.RUNNING.value
            job.attempts += 1
            job.locked_by = worker_id
            job.locked_until = lock_until
            job.started_at = job.started_at or now
            job.error_code = None
            job.error_message = None
        await self.session.flush()
        return jobs

    async def update_job(self, job: JobQueueItem) -> JobQueueItem:
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def add_event(self, event: JobQueueEvent) -> JobQueueEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(self, job_id: UUID) -> list[JobQueueEvent]:
        statement: Select[tuple[JobQueueEvent]] = (
            select(JobQueueEvent)
            .where(JobQueueEvent.job_id == job_id)
            .order_by(JobQueueEvent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_jobs_by_status(
        self,
        queue_name: str | None = None,
    ) -> dict[str, int]:
        statement = select(JobQueueItem.status, func.count()).group_by(JobQueueItem.status)
        if queue_name is not None:
            statement = statement.where(JobQueueItem.queue_name == queue_name)
        result = await self.session.execute(statement)
        return {str(status): int(count) for status, count in result.all()}


def is_idempotency_integrity_error(error: IntegrityError) -> bool:
    return "job_queue_items" in str(error.orig) and "idempotency" in str(error.orig)
