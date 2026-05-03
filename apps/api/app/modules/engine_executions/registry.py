from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.engine_executions.models import EngineExecutionPriority, EngineExecutionRecord
from app.modules.engine_executions.schemas import EngineExecutionCreate
from app.modules.engine_executions.service import EngineExecutionService


class EngineOperationRegistry:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.service = EngineExecutionService(session, settings=settings)

    async def record_analysis_operation(
        self,
        workspace_id: UUID,
        idempotency_key: str,
        input_json: dict[str, Any],
        source_id: UUID | None = None,
        engine_version: str | None = None,
        priority: EngineExecutionPriority | None = None,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        return await self.record_operation(
            workspace_id=workspace_id,
            engine_name="analysis_lifecycle",
            engine_version=engine_version,
            operation_type="analysis.run",
            idempotency_key=idempotency_key,
            input_json=input_json,
            source_type="analysis_run",
            source_id=source_id,
            priority=priority,
            commit=commit,
        )

    async def record_replay_operation(
        self,
        workspace_id: UUID,
        idempotency_key: str,
        input_json: dict[str, Any],
        source_id: UUID | None = None,
        engine_version: str | None = None,
        priority: EngineExecutionPriority | None = None,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        return await self.record_operation(
            workspace_id=workspace_id,
            engine_name="analysis_replay",
            engine_version=engine_version,
            operation_type="replay.run",
            idempotency_key=idempotency_key,
            input_json=input_json,
            source_type="analysis_run",
            source_id=source_id,
            priority=priority,
            commit=commit,
        )

    async def record_outcome_operation(
        self,
        workspace_id: UUID,
        idempotency_key: str,
        input_json: dict[str, Any],
        source_id: UUID | None = None,
        engine_version: str | None = None,
        priority: EngineExecutionPriority | None = None,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        return await self.record_operation(
            workspace_id=workspace_id,
            engine_name="outcome_evaluation",
            engine_version=engine_version,
            operation_type="outcomes.evaluate",
            idempotency_key=idempotency_key,
            input_json=input_json,
            source_type="signal",
            source_id=source_id,
            priority=priority,
            commit=commit,
        )

    async def record_reasoning_operation(
        self,
        workspace_id: UUID,
        idempotency_key: str,
        input_json: dict[str, Any],
        source_id: UUID | None = None,
        engine_version: str | None = None,
        priority: EngineExecutionPriority | None = None,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        return await self.record_operation(
            workspace_id=workspace_id,
            engine_name="scenario_reasoning",
            engine_version=engine_version,
            operation_type="reasoning.generate",
            idempotency_key=idempotency_key,
            input_json=input_json,
            source_type="reasoning_run",
            source_id=source_id,
            priority=priority,
            commit=commit,
        )

    async def record_scan_operation(
        self,
        workspace_id: UUID,
        idempotency_key: str,
        input_json: dict[str, Any],
        source_id: UUID | None = None,
        engine_version: str | None = None,
        priority: EngineExecutionPriority | None = None,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        return await self.record_operation(
            workspace_id=workspace_id,
            engine_name="market_scan",
            engine_version=engine_version,
            operation_type="market_scan.run",
            idempotency_key=idempotency_key,
            input_json=input_json,
            source_type="market_scan",
            source_id=source_id,
            priority=priority,
            commit=commit,
        )

    async def record_operation(
        self,
        workspace_id: UUID,
        engine_name: str,
        operation_type: str,
        idempotency_key: str,
        input_json: dict[str, Any],
        engine_version: str | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        priority: EngineExecutionPriority | None = None,
        force: bool = False,
        commit: bool = True,
    ) -> EngineExecutionRecord:
        return await self.service.create_record(
            EngineExecutionCreate(
                workspace_id=workspace_id,
                engine_name=engine_name,
                engine_version=engine_version,
                operation_type=operation_type,
                idempotency_key=idempotency_key,
                priority=priority,
                source_type=source_type,
                source_id=source_id,
                input_json=input_json,
                force=force,
            ),
            commit=commit,
        )
