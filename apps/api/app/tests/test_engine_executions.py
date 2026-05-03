from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from app.config import AppEnvironment, Settings
from app.modules.engine_executions.models import (
    EngineExecutionEvent,
    EngineExecutionRecord,
    EngineExecutionStatus,
)
from app.modules.engine_executions.repository import EngineExecutionRepository
from app.modules.engine_executions.schemas import EngineExecutionCreate
from app.modules.engine_executions.service import EngineExecutionService, forced_key


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class FakeEngineExecutionRepository:
    def __init__(self) -> None:
        self.records: dict[UUID, EngineExecutionRecord] = {}
        self.records_by_key: dict[tuple[UUID, str], EngineExecutionRecord] = {}
        self.events: list[EngineExecutionEvent] = []

    async def create_record(self, record: EngineExecutionRecord) -> EngineExecutionRecord:
        self.ensure_record_fields(record)
        self.records[record.id] = record
        self.records_by_key[(record.workspace_id, record.idempotency_key)] = record
        return record

    async def get_record(self, record_id: UUID) -> EngineExecutionRecord | None:
        return self.records.get(record_id)

    async def get_by_idempotency_key(
        self,
        workspace_id: UUID,
        idempotency_key: str,
    ) -> EngineExecutionRecord | None:
        return self.records_by_key.get((workspace_id, idempotency_key))

    async def add_event(self, event: EngineExecutionEvent) -> EngineExecutionEvent:
        now = datetime(2026, 5, 2, tzinfo=UTC)
        event.id = uuid4()
        event.created_at = now
        self.events.append(event)
        return event

    async def update_record(self, record: EngineExecutionRecord) -> EngineExecutionRecord:
        record.updated_at = datetime(2026, 5, 2, tzinfo=UTC)
        self.records[record.id] = record
        return record

    def ensure_record_fields(self, record: EngineExecutionRecord) -> None:
        now = datetime(2026, 5, 2, tzinfo=UTC)
        record.id = uuid4()
        record.created_at = now
        record.updated_at = now
        if record.attempts is None:
            record.attempts = 0


def make_service(repository: FakeEngineExecutionRepository) -> EngineExecutionService:
    service = EngineExecutionService(
        cast(Any, FakeSession()),
        settings=Settings(_env_file=None, app_env=AppEnvironment.TEST),
    )
    service.repository = cast(EngineExecutionRepository, repository)
    return service


@pytest.mark.asyncio
async def test_create_record_is_idempotent_by_workspace_key() -> None:
    workspace_id = uuid4()
    repository = FakeEngineExecutionRepository()
    service = make_service(repository)
    payload = EngineExecutionCreate(
        workspace_id=workspace_id,
        engine_name="analysis_lifecycle",
        operation_type="analysis.run",
        idempotency_key="analysis.run:test",
        input_json={"timeframe": "15m"},
    )

    first = await service.create_record(payload)
    second = await service.create_record(payload)

    assert first.id == second.id
    assert len(repository.records) == 1
    assert first.status == EngineExecutionStatus.PENDING.value


def test_forced_key_preserves_length_limit_and_original_prefix() -> None:
    key = forced_key("x" * 400)

    assert len(key) <= 240
    assert key.startswith("x")
    assert ":forced:" in key
