from datetime import datetime, timedelta
from typing import Any, cast
from uuid import uuid4

import pytest

from app.config import AppEnvironment, Settings
from app.core.time import utc_now
from app.modules.runtime_supervisor.models import (
    RuntimeRunRequestStatus,
    RuntimeRunRequestType,
    RuntimeWorkerDefinition,
    RuntimeWorkerInstance,
    RuntimeWorkerInstanceStatus,
    RuntimeWorkerRunRequest,
)
from app.modules.runtime_supervisor.repository import RuntimeSupervisorRepository
from app.modules.runtime_supervisor.schemas import (
    RuntimeRunRequestCreate,
    RuntimeWorkerInstanceHeartbeat,
)
from app.modules.runtime_supervisor.service import RuntimeSupervisorService


class FakeSession:
    async def commit(self) -> None:
        return None

    async def flush(self) -> None:
        return None

    async def refresh(self, item: object) -> None:
        return None


class FakeRuntimeSupervisorRepository:
    def __init__(self) -> None:
        self.definitions: dict[str, RuntimeWorkerDefinition] = {}
        self.instances: dict[str, RuntimeWorkerInstance] = {}
        self.run_requests: dict[object, RuntimeWorkerRunRequest] = {}

    async def upsert_worker_definition(
        self,
        definition: RuntimeWorkerDefinition,
    ) -> tuple[RuntimeWorkerDefinition, bool]:
        created = definition.key not in self.definitions
        self.definitions[definition.key] = definition
        return definition, created

    async def list_worker_definitions(
        self,
        status: str | None = None,
        worker_type: str | None = None,
    ) -> list[RuntimeWorkerDefinition]:
        definitions = list(self.definitions.values())
        if status is not None:
            definitions = [definition for definition in definitions if definition.status == status]
        if worker_type is not None:
            definitions = [
                definition for definition in definitions if definition.worker_type == worker_type
            ]
        return definitions

    async def get_worker_definition(self, key: str) -> RuntimeWorkerDefinition | None:
        return self.definitions.get(key)

    async def get_worker_instance_by_worker_id(
        self,
        worker_id: str,
    ) -> RuntimeWorkerInstance | None:
        return self.instances.get(worker_id)

    async def create_worker_instance(
        self,
        instance: RuntimeWorkerInstance,
    ) -> RuntimeWorkerInstance:
        instance.id = uuid4()
        self.instances[instance.worker_id] = instance
        return instance

    async def update_worker_instance(
        self,
        instance: RuntimeWorkerInstance,
    ) -> RuntimeWorkerInstance:
        self.instances[instance.worker_id] = instance
        return instance

    async def list_worker_instances(
        self,
        limit: int,
        offset: int,
        worker_definition_key: str | None = None,
        workspace_id: object | None = None,
        status: str | None = None,
    ) -> list[RuntimeWorkerInstance]:
        instances = list(self.instances.values())
        if worker_definition_key is not None:
            instances = [
                instance
                for instance in instances
                if instance.worker_definition_key == worker_definition_key
            ]
        if status is not None:
            instances = [instance for instance in instances if instance.status == status]
        return instances[offset : offset + limit]

    async def mark_stale_workers(self, stale_before: datetime) -> list[RuntimeWorkerInstance]:
        stale_instances: list[RuntimeWorkerInstance] = []
        for instance in self.instances.values():
            if instance.last_heartbeat_at is None:
                continue
            if instance.status not in {"starting", "running", "unknown"}:
                continue
            if instance.last_heartbeat_at < stale_before:
                instance.status = RuntimeWorkerInstanceStatus.STALE.value
                stale_instances.append(instance)
        return stale_instances

    async def create_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
    ) -> RuntimeWorkerRunRequest:
        run_request.id = uuid4()
        self.run_requests[run_request.id] = run_request
        return run_request

    async def get_run_request(self, request_id: object) -> RuntimeWorkerRunRequest | None:
        return self.run_requests.get(request_id)

    async def update_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
    ) -> RuntimeWorkerRunRequest:
        self.run_requests[run_request.id] = run_request
        return run_request

    async def count_run_requests_by_status(
        self,
        workspace_id: object | None = None,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for run_request in self.run_requests.values():
            counts[run_request.status] = counts.get(run_request.status, 0) + 1
        return counts

    async def count_run_requests_by_worker(
        self,
        workspace_id: object | None = None,
    ) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for run_request in self.run_requests.values():
            worker_counts = counts.setdefault(run_request.worker_definition_key, {})
            worker_counts[run_request.status] = worker_counts.get(run_request.status, 0) + 1
        return counts


def make_service() -> tuple[RuntimeSupervisorService, FakeRuntimeSupervisorRepository]:
    repository = FakeRuntimeSupervisorRepository()
    service = RuntimeSupervisorService(
        cast(Any, FakeSession()),
        settings=Settings(_env_file=None, app_env=AppEnvironment.TEST),
        repository=cast(RuntimeSupervisorRepository, repository),
    )
    return service, repository


@pytest.mark.asyncio
async def test_seed_default_worker_definitions_records_available_workers() -> None:
    service, repository = make_service()

    result = await service.seed_default_worker_definitions()

    assert result.seeded_count >= 4
    assert "live_feed_worker" in result.worker_keys
    assert "market_scan_worker" in repository.definitions


@pytest.mark.asyncio
async def test_heartbeat_and_stale_marking_update_worker_instance_status() -> None:
    service, repository = make_service()
    await service.seed_default_worker_definitions()

    instance = await service.heartbeat(
        RuntimeWorkerInstanceHeartbeat(
            worker_definition_key="live_feed_worker",
            worker_id="worker-1",
            payload={"activeSubscriptionTasks": 0},
        )
    )
    instance.last_heartbeat_at = utc_now() - timedelta(minutes=10)

    stale_instances, _ = await service.mark_stale_workers()

    assert stale_instances == [instance]
    assert repository.instances["worker-1"].status == RuntimeWorkerInstanceStatus.STALE.value


@pytest.mark.asyncio
async def test_run_request_records_unsupported_without_executing_shell_commands() -> None:
    service, _ = make_service()
    await service.seed_default_worker_definitions()

    run_request = await service.create_run_request(
        RuntimeRunRequestCreate(
            worker_definition_key="live_feed_worker",
            request_type=RuntimeRunRequestType.RUN_ONCE,
        )
    )

    assert run_request.status == RuntimeRunRequestStatus.UNSUPPORTED.value
    assert run_request.error_message is not None
