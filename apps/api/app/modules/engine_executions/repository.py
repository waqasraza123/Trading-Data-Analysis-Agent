from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, case, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engine_executions.models import (
    EngineExecutionEvent,
    EngineExecutionPriority,
    EngineExecutionRecord,
    EngineExecutionStatus,
)


class EngineExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_record(self, record: EngineExecutionRecord) -> EngineExecutionRecord:
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_record(self, record_id: UUID) -> EngineExecutionRecord | None:
        return await self.session.get(EngineExecutionRecord, record_id)

    async def get_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> EngineExecutionRecord | None:
        statement: Select[tuple[EngineExecutionRecord]] = select(EngineExecutionRecord).where(
            EngineExecutionRecord.workspace_id == workspace_id,
            EngineExecutionRecord.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_records(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: str | None = None,
        engine_name: str | None = None,
        operation_type: str | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
    ) -> list[EngineExecutionRecord]:
        statement: Select[tuple[EngineExecutionRecord]] = (
            select(EngineExecutionRecord)
            .order_by(EngineExecutionRecord.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workspace_id is not None:
            statement = statement.where(EngineExecutionRecord.workspace_id == workspace_id)
        if status is not None:
            statement = statement.where(EngineExecutionRecord.status == status)
        if engine_name is not None:
            statement = statement.where(EngineExecutionRecord.engine_name == engine_name)
        if operation_type is not None:
            statement = statement.where(EngineExecutionRecord.operation_type == operation_type)
        if source_type is not None:
            statement = statement.where(EngineExecutionRecord.source_type == source_type)
        if source_id is not None:
            statement = statement.where(EngineExecutionRecord.source_id == source_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def claim_pending_records(
        self,
        now: datetime,
        worker_id: str,
        limit: int,
        lock_seconds: int,
        workspace_id: UUID | None = None,
    ) -> list[EngineExecutionRecord]:
        lock_until = now + timedelta(seconds=lock_seconds)
        priority_order = case(
            (EngineExecutionRecord.priority == EngineExecutionPriority.HIGH.value, 0),
            (EngineExecutionRecord.priority == EngineExecutionPriority.NORMAL.value, 1),
            else_=2,
        )
        statement: Select[tuple[EngineExecutionRecord]] = (
            select(EngineExecutionRecord)
            .where(
                EngineExecutionRecord.attempts < EngineExecutionRecord.max_attempts,
                or_(
                    EngineExecutionRecord.status == EngineExecutionStatus.PENDING.value,
                    and_(
                        EngineExecutionRecord.status == EngineExecutionStatus.RUNNING.value,
                        EngineExecutionRecord.locked_until.is_not(None),
                        EngineExecutionRecord.locked_until <= now,
                    ),
                ),
                or_(
                    EngineExecutionRecord.locked_by.is_(None),
                    EngineExecutionRecord.locked_until.is_(None),
                    EngineExecutionRecord.locked_until <= now,
                ),
            )
            .order_by(priority_order.asc(), EngineExecutionRecord.created_at.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        if workspace_id is not None:
            statement = statement.where(EngineExecutionRecord.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        records = list(result.scalars().all())
        for record in records:
            record.status = EngineExecutionStatus.RUNNING.value
            record.attempts += 1
            record.locked_by = worker_id
            record.locked_until = lock_until
            record.started_at = record.started_at or now
            record.error_code = None
            record.error_message = None
        await self.session.flush()
        return records

    async def update_record(self, record: EngineExecutionRecord) -> EngineExecutionRecord:
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def add_event(self, event: EngineExecutionEvent) -> EngineExecutionEvent:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list_events(self, record_id: UUID) -> list[EngineExecutionEvent]:
        statement: Select[tuple[EngineExecutionEvent]] = (
            select(EngineExecutionEvent)
            .where(EngineExecutionEvent.execution_record_id == record_id)
            .order_by(EngineExecutionEvent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
