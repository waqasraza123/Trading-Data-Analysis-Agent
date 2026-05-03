from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.engine_executions.models import (
    EngineExecutionEvent,
    EngineExecutionEventType,
    EngineExecutionPriority,
    EngineExecutionRecord,
    EngineExecutionStatus,
)
from app.modules.engine_executions.repository import EngineExecutionRepository
from app.modules.engine_executions.schemas import EngineExecutionCreate

DEFAULT_ENGINE_EXECUTION_WORKER_ID = "engine-execution-registry"


class EngineExecutionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = EngineExecutionRepository(session)

    async def create_record(
        self,
        payload: EngineExecutionCreate,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        existing = await self.repository.get_by_idempotency_key(
            payload.workspace_id,
            payload.idempotency_key,
        )
        if existing is not None and not payload.force:
            return existing
        idempotency_key = (
            payload.idempotency_key if not payload.force else forced_key(payload.idempotency_key)
        )
        max_attempts = payload.max_attempts or self.settings.engine_execution_default_max_attempts
        priority = payload.priority or EngineExecutionPriority(
            self.settings.engine_execution_default_priority
        )
        record = EngineExecutionRecord(
            workspace_id=payload.workspace_id,
            engine_name=payload.engine_name,
            engine_version=payload.engine_version,
            operation_type=payload.operation_type,
            idempotency_key=idempotency_key,
            status=EngineExecutionStatus.PENDING.value,
            priority=priority.value,
            source_type=payload.source_type,
            source_id=payload.source_id,
            input_json=payload.input_json,
            max_attempts=max_attempts,
        )
        try:
            created_record = await self.repository.create_record(record)
            await self.add_event(
                created_record.id,
                EngineExecutionEventType.CREATED,
                "Engine task record created",
                {"operationType": created_record.operation_type},
                commit=False,
            )
            if commit:
                await self.session.commit()
            return created_record
        except IntegrityError as error:
            await self.session.rollback()
            existing_after_conflict = await self.repository.get_by_idempotency_key(
                payload.workspace_id,
                payload.idempotency_key,
            )
            if existing_after_conflict is not None and not payload.force:
                return existing_after_conflict
            raise AppError(
                409,
                "engine_execution_idempotency_conflict",
                "Engine execution record could not be created",
            ) from error

    async def get_record(self, record_id: UUID) -> EngineExecutionRecord:
        record = await self.repository.get_record(record_id)
        if record is None:
            raise AppError(404, "engine_execution_not_found", "Engine execution record not found")
        return record

    async def get_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> EngineExecutionRecord:
        record = await self.repository.get_by_idempotency_key(workspace_id, idempotency_key)
        if record is None:
            raise AppError(404, "engine_execution_not_found", "Engine execution record not found")
        return record

    async def list_records(
        self,
        limit: int,
        offset: int,
        workspace_id: UUID | None = None,
        status: EngineExecutionStatus | None = None,
        engine_name: str | None = None,
        operation_type: str | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
    ) -> list[EngineExecutionRecord]:
        return await self.repository.list_records(
            limit=limit,
            offset=offset,
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
            engine_name=engine_name,
            operation_type=operation_type,
            source_type=source_type,
            source_id=source_id,
        )

    async def start_record(
        self,
        record_id: UUID,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        record = await self.get_record(record_id)
        if record.status in terminal_statuses():
            raise AppError(
                422,
                "engine_execution_not_startable",
                "Completed, failed, skipped, or cancelled records cannot be started",
            )
        now = utc_now()
        record.status = EngineExecutionStatus.RUNNING.value
        record.started_at = record.started_at or now
        record.locked_by = None
        record.locked_until = None
        await self.add_event(
            record.id,
            EngineExecutionEventType.STARTED,
            "Engine task started",
            commit=False,
        )
        await self.repository.update_record(record)
        if commit:
            await self.session.commit()
        return record

    async def complete_record(
        self,
        record_id: UUID,
        output: dict[str, Any],
        artifacts: list[dict[str, Any]] | None = None,
        completed_with_warnings: bool = False,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        record = await self.get_record(record_id)
        if record.status in {
            EngineExecutionStatus.CANCELLED.value,
            EngineExecutionStatus.SKIPPED.value,
        }:
            raise AppError(
                422,
                "engine_execution_not_completable",
                "Cancelled or skipped records cannot be completed",
            )
        record.status = (
            EngineExecutionStatus.COMPLETED_WITH_WARNINGS.value
            if completed_with_warnings
            else EngineExecutionStatus.COMPLETED.value
        )
        record.output_json = output
        record.produced_artifacts_json = artifacts or []
        record.error_code = None
        record.error_message = None
        record.locked_by = None
        record.locked_until = None
        record.completed_at = utc_now()
        if artifacts:
            await self.add_event(
                record.id,
                EngineExecutionEventType.ARTIFACT_RECORDED,
                "Engine task artifacts recorded",
                {"artifactCount": len(artifacts)},
                commit=False,
            )
        await self.add_event(
            record.id,
            EngineExecutionEventType.COMPLETED,
            "Engine task completed",
            {"completedWithWarnings": completed_with_warnings},
            commit=False,
        )
        await self.repository.update_record(record)
        if commit:
            await self.session.commit()
        return record

    async def fail_record(
        self,
        record_id: UUID,
        error_code: str,
        error_message: str,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        record = await self.get_record(record_id)
        if record.status in terminal_statuses() - {EngineExecutionStatus.FAILED.value}:
            raise AppError(
                422,
                "engine_execution_not_failable",
                "Completed, skipped, or cancelled records cannot be failed",
            )
        record.status = EngineExecutionStatus.FAILED.value
        record.error_code = error_code
        record.error_message = error_message
        record.locked_by = None
        record.locked_until = None
        record.completed_at = utc_now()
        await self.add_event(
            record.id,
            EngineExecutionEventType.FAILED,
            "Engine task failed",
            {"errorCode": error_code},
            commit=False,
        )
        await self.repository.update_record(record)
        if commit:
            await self.session.commit()
        return record

    async def skip_record(
        self,
        record_id: UUID,
        reason: str,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        record = await self.get_record(record_id)
        if record.status in terminal_statuses():
            return record
        record.status = EngineExecutionStatus.SKIPPED.value
        record.output_json = {"reason": reason}
        record.locked_by = None
        record.locked_until = None
        record.completed_at = utc_now()
        await self.add_event(
            record.id,
            EngineExecutionEventType.SKIPPED,
            "Engine task skipped",
            {"reason": reason},
            commit=False,
        )
        await self.repository.update_record(record)
        if commit:
            await self.session.commit()
        return record

    async def cancel_record(self, record_id: UUID, commit: bool = True) -> EngineExecutionRecord:
        record = await self.get_record(record_id)
        if record.status in terminal_statuses():
            return record
        record.status = EngineExecutionStatus.CANCELLED.value
        record.locked_by = None
        record.locked_until = None
        record.completed_at = utc_now()
        await self.add_event(
            record.id,
            EngineExecutionEventType.CANCELLED,
            "Engine task cancelled",
            commit=False,
        )
        await self.repository.update_record(record)
        if commit:
            await self.session.commit()
        return record

    async def claim_pending_records(
        self,
        workspace_id: UUID | None = None,
        limit: int = 50,
        worker_id: str = DEFAULT_ENGINE_EXECUTION_WORKER_ID,
        commit: bool = True,
    ) -> list[EngineExecutionRecord]:
        records = await self.repository.claim_pending_records(
            now=utc_now(),
            worker_id=worker_id,
            limit=limit,
            lock_seconds=self.settings.engine_execution_lock_seconds,
            workspace_id=workspace_id,
        )
        for record in records:
            await self.add_event(
                record.id,
                EngineExecutionEventType.CLAIMED,
                "Engine task claimed",
                {"workerId": worker_id, "attempts": record.attempts},
                commit=False,
            )
        if commit:
            await self.session.commit()
        return records

    async def add_event(
        self,
        record_id: UUID,
        event_type: EngineExecutionEventType,
        message: str,
        metadata_json: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> EngineExecutionEvent:
        record = await self.get_record(record_id)
        event = await self.repository.add_event(
            EngineExecutionEvent(
                workspace_id=record.workspace_id,
                execution_record_id=record.id,
                event_type=event_type.value,
                message=message,
                metadata_json=metadata_json or {},
            )
        )
        if commit:
            await self.session.commit()
        return event

    async def list_events(self, record_id: UUID) -> list[EngineExecutionEvent]:
        await self.get_record(record_id)
        return await self.repository.list_events(record_id)


def forced_key(idempotency_key: str) -> str:
    suffix = uuid4().hex
    max_prefix_length = 240 - len(":forced:") - len(suffix)
    return f"{idempotency_key[:max_prefix_length]}:forced:{suffix}"


def terminal_statuses() -> set[str]:
    return {
        EngineExecutionStatus.COMPLETED.value,
        EngineExecutionStatus.COMPLETED_WITH_WARNINGS.value,
        EngineExecutionStatus.SKIPPED.value,
        EngineExecutionStatus.FAILED.value,
        EngineExecutionStatus.CANCELLED.value,
    }
