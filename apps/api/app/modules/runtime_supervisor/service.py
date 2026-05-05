from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.runner import ReasoningActionRunner
from app.modules.market_scans.scanner import MarketScanExecutor
from app.modules.runtime_supervisor.models import (
    RuntimeRunRequestStatus,
    RuntimeRunRequestType,
    RuntimeWorkerDefinition,
    RuntimeWorkerDefinitionStatus,
    RuntimeWorkerInstance,
    RuntimeWorkerInstanceStatus,
    RuntimeWorkerRunRequest,
)
from app.modules.runtime_supervisor.registry import default_worker_definitions
from app.modules.runtime_supervisor.repository import RuntimeSupervisorRepository
from app.modules.runtime_supervisor.schemas import (
    RuntimeHealthWorkerSummary,
    RuntimeRunRequestCreate,
    RuntimeSupervisorHealth,
    RuntimeWorkerInstanceHeartbeat,
)


@dataclass(frozen=True)
class RuntimeWorkerSeedResult:
    seeded_count: int
    updated_count: int
    worker_keys: list[str]


class RuntimeSupervisorService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: RuntimeSupervisorRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or RuntimeSupervisorRepository(session)

    async def seed_default_worker_definitions(self) -> RuntimeWorkerSeedResult:
        seeded_count = 0
        updated_count = 0
        worker_keys: list[str] = []
        for spec in default_worker_definitions(self.settings):
            _, created = await self.repository.upsert_worker_definition(
                RuntimeWorkerDefinition(
                    key=spec.key,
                    name=spec.name,
                    description=spec.description,
                    worker_type=spec.worker_type.value,
                    status=spec.status.value,
                    command=spec.command,
                    required_settings_json=list(spec.required_settings),
                    optional_settings_json=list(spec.optional_settings),
                    safety_notes_json=list(spec.safety_notes),
                    metadata_json=spec.metadata,
                )
            )
            if created:
                seeded_count += 1
            else:
                updated_count += 1
            worker_keys.append(spec.key)
        await self.session.commit()
        return RuntimeWorkerSeedResult(
            seeded_count=seeded_count,
            updated_count=updated_count,
            worker_keys=worker_keys,
        )

    async def list_worker_definitions(
        self,
        status: RuntimeWorkerDefinitionStatus | None = None,
        worker_type: str | None = None,
    ) -> list[RuntimeWorkerDefinition]:
        return await self.repository.list_worker_definitions(
            status=status.value if status is not None else None,
            worker_type=worker_type,
        )

    async def get_worker_definition(self, key: str) -> RuntimeWorkerDefinition:
        definition = await self.repository.get_worker_definition(key)
        if definition is None:
            raise AppError(404, "runtime_worker_definition_not_found", "Runtime worker not found")
        return definition

    async def register_worker_instance(
        self,
        payload: RuntimeWorkerInstanceHeartbeat,
    ) -> RuntimeWorkerInstance:
        return await self.heartbeat(payload)

    async def heartbeat(self, payload: RuntimeWorkerInstanceHeartbeat) -> RuntimeWorkerInstance:
        if not self.settings.runtime_worker_heartbeat_enabled:
            raise AppError(
                403,
                "runtime_worker_heartbeat_disabled",
                "Runtime worker heartbeat is disabled",
            )
        await self.get_worker_definition(payload.worker_definition_key)
        now = utc_now()
        existing = await self.repository.get_worker_instance_by_worker_id(payload.worker_id)
        if existing is None:
            instance = await self.repository.create_worker_instance(
                RuntimeWorkerInstance(
                    workspace_id=payload.workspace_id,
                    worker_definition_key=payload.worker_definition_key,
                    worker_id=payload.worker_id,
                    status=payload.status.value,
                    host_name=payload.host_name,
                    process_id=payload.process_id,
                    started_at=now,
                    last_heartbeat_at=now,
                    stopped_at=(
                        now if payload.status == RuntimeWorkerInstanceStatus.STOPPED else None
                    ),
                    heartbeat_payload_json=payload.payload,
                    metadata_json=payload.metadata,
                )
            )
        else:
            existing.workspace_id = payload.workspace_id
            existing.worker_definition_key = payload.worker_definition_key
            existing.status = payload.status.value
            existing.host_name = payload.host_name
            existing.process_id = payload.process_id
            existing.last_heartbeat_at = now
            existing.heartbeat_payload_json = payload.payload
            existing.metadata_json = {**existing.metadata_json, **payload.metadata}
            if existing.started_at is None and payload.status in {
                RuntimeWorkerInstanceStatus.STARTING,
                RuntimeWorkerInstanceStatus.RUNNING,
            }:
                existing.started_at = now
            if payload.status == RuntimeWorkerInstanceStatus.STOPPED:
                existing.stopped_at = now
            elif payload.status == RuntimeWorkerInstanceStatus.RUNNING:
                existing.stopped_at = None
            instance = await self.repository.update_worker_instance(existing)
        await self.session.commit()
        return instance

    async def mark_stale_workers(self) -> tuple[list[RuntimeWorkerInstance], object]:
        stale_before = utc_now() - timedelta(seconds=self.settings.runtime_worker_stale_seconds)
        instances = await self.repository.mark_stale_workers(stale_before)
        await self.session.commit()
        return instances, stale_before

    async def list_worker_instances(
        self,
        limit: int,
        offset: int,
        worker_definition_key: str | None = None,
        workspace_id: UUID | None = None,
        status: RuntimeWorkerInstanceStatus | None = None,
    ) -> list[RuntimeWorkerInstance]:
        return await self.repository.list_worker_instances(
            limit=limit,
            offset=offset,
            worker_definition_key=worker_definition_key,
            workspace_id=workspace_id,
            status=status.value if status is not None else None,
        )

    async def create_run_request(
        self,
        payload: RuntimeRunRequestCreate,
    ) -> RuntimeWorkerRunRequest:
        if not self.settings.runtime_supervisor_run_requests_enabled:
            raise AppError(
                403,
                "runtime_supervisor_run_requests_disabled",
                "Runtime supervisor run requests are disabled",
            )
        definition = await self.get_worker_definition(payload.worker_definition_key)
        now = utc_now()
        run_request = await self.repository.create_run_request(
            RuntimeWorkerRunRequest(
                workspace_id=payload.workspace_id,
                worker_definition_key=payload.worker_definition_key,
                status=RuntimeRunRequestStatus.PENDING.value,
                requested_by_user_id=payload.requested_by_user_id,
                request_type=payload.request_type.value,
                input_json=payload.input_json,
            )
        )
        await self.session.flush()
        await self.execute_supported_run_request(run_request, definition, now)
        await self.session.commit()
        await self.session.refresh(run_request)
        return run_request

    async def get_run_request(self, request_id: UUID) -> RuntimeWorkerRunRequest:
        run_request = await self.repository.get_run_request(request_id)
        if run_request is None:
            raise AppError(404, "runtime_worker_run_request_not_found", "Run request not found")
        return run_request

    async def complete_run_request(
        self,
        request_id: UUID,
        result_json: dict[str, Any] | None = None,
        completed_with_warnings: bool = False,
    ) -> RuntimeWorkerRunRequest:
        run_request = await self.get_run_request(request_id)
        run_request.status = (
            RuntimeRunRequestStatus.COMPLETED_WITH_WARNINGS.value
            if completed_with_warnings
            else RuntimeRunRequestStatus.COMPLETED.value
        )
        run_request.result_json = result_json or {}
        run_request.completed_at = utc_now()
        updated = await self.repository.update_run_request(run_request)
        await self.session.commit()
        return updated

    async def fail_run_request(
        self,
        request_id: UUID,
        error_message: str,
    ) -> RuntimeWorkerRunRequest:
        run_request = await self.get_run_request(request_id)
        run_request.status = RuntimeRunRequestStatus.FAILED.value
        run_request.error_message = error_message[:2000]
        run_request.completed_at = utc_now()
        updated = await self.repository.update_run_request(run_request)
        await self.session.commit()
        return updated

    async def summarize_runtime_health(
        self,
        workspace_id: UUID | None = None,
    ) -> RuntimeSupervisorHealth:
        definitions = await self.repository.list_worker_definitions()
        instances = await self.repository.list_worker_instances(
            limit=1000,
            offset=0,
            workspace_id=workspace_id,
        )
        run_request_counts = await self.repository.count_run_requests_by_status(workspace_id)
        run_request_worker_counts = await self.repository.count_run_requests_by_worker(workspace_id)
        worker_summaries = [
            build_worker_summary(definition, instances, run_request_worker_counts)
            for definition in definitions
        ]
        running_instance_count = count_instances(instances, RuntimeWorkerInstanceStatus.RUNNING)
        stale_instance_count = count_instances(instances, RuntimeWorkerInstanceStatus.STALE)
        status = runtime_health_status(
            definitions=definitions,
            stale_instance_count=stale_instance_count,
            failed_run_request_count=run_request_counts.get(
                RuntimeRunRequestStatus.FAILED.value,
                0,
            ),
        )
        return RuntimeSupervisorHealth(
            status=status,
            supervisor_version=self.settings.runtime_supervisor_version,
            heartbeat_enabled=self.settings.runtime_worker_heartbeat_enabled,
            run_requests_enabled=self.settings.runtime_supervisor_run_requests_enabled,
            stale_after_seconds=self.settings.runtime_worker_stale_seconds,
            worker_count=len(definitions),
            available_worker_count=count_definitions(
                definitions,
                RuntimeWorkerDefinitionStatus.AVAILABLE,
            ),
            disabled_worker_count=count_definitions(
                definitions,
                RuntimeWorkerDefinitionStatus.DISABLED,
            ),
            running_instance_count=running_instance_count,
            stale_instance_count=stale_instance_count,
            pending_run_request_count=run_request_counts.get(
                RuntimeRunRequestStatus.PENDING.value,
                0,
            ),
            running_run_request_count=run_request_counts.get(
                RuntimeRunRequestStatus.RUNNING.value,
                0,
            ),
            failed_run_request_count=run_request_counts.get(
                RuntimeRunRequestStatus.FAILED.value,
                0,
            ),
            workers=worker_summaries,
            operation_counts={"runtime_run_requests": run_request_counts},
        )

    async def execute_supported_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
        definition: RuntimeWorkerDefinition,
        now: datetime,
    ) -> None:
        if run_request.request_type == RuntimeRunRequestType.REFRESH_STATUS.value:
            run_request.status = RuntimeRunRequestStatus.COMPLETED.value
            run_request.started_at = run_request.started_at or now
            run_request.completed_at = now
            run_request.result_json = {
                "workerDefinitionKey": definition.key,
                "definitionStatus": definition.status,
                "message": "Runtime status refresh recorded.",
            }
            return
        if run_request.request_type == RuntimeRunRequestType.DRY_RUN.value:
            run_request.status = RuntimeRunRequestStatus.COMPLETED.value
            run_request.started_at = run_request.started_at or now
            run_request.completed_at = now
            run_request.result_json = {
                "workerDefinitionKey": definition.key,
                "requestType": run_request.request_type,
                "safeExecutionAvailable": definition.key
                in {"reasoning_actions_worker", "market_scan_worker"},
                "dryRun": True,
            }
            return
        if run_request.request_type != RuntimeRunRequestType.EXECUTE_DUE.value:
            mark_unsupported(
                run_request,
                now,
                "Run request type is not supported for API execution",
            )
            return
        if definition.status != RuntimeWorkerDefinitionStatus.AVAILABLE.value:
            mark_unsupported(run_request, now, "Runtime worker is not available")
            return
        if definition.key == "reasoning_actions_worker":
            await self.execute_reasoning_actions_run_request(run_request, now)
            return
        if definition.key == "market_scan_worker":
            await self.execute_market_scan_run_request(run_request, now)
            return
        mark_unsupported(
            run_request,
            now,
            "No safe runtime supervisor integration is registered for this worker",
        )

    async def execute_reasoning_actions_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
        now: datetime,
    ) -> None:
        limit = bounded_limit(
            run_request.input_json.get("limit"),
            self.settings.reasoning_action_worker_batch_size,
            500,
        )
        run_request.status = RuntimeRunRequestStatus.RUNNING.value
        run_request.started_at = now
        await self.session.flush()
        result = await ReasoningActionRunner(
            settings=self.settings,
            session=self.session,
            worker_id=f"runtime-supervisor-{run_request.id}",
        ).execute_due_actions(workspace_id=run_request.workspace_id, limit=limit)
        run_request.status = final_run_status(result.failed_count, result.skipped_count)
        run_request.completed_at = utc_now()
        run_request.result_json = {
            "workerRunId": str(result.worker_run.id),
            "claimedCount": result.claimed_count,
            "completedCount": result.completed_count,
            "skippedCount": result.skipped_count,
            "failedCount": result.failed_count,
        }

    async def execute_market_scan_run_request(
        self,
        run_request: RuntimeWorkerRunRequest,
        now: datetime,
    ) -> None:
        limit = bounded_limit(
            run_request.input_json.get("limit"),
            self.settings.market_scan_worker_batch_size,
            500,
        )
        run_request.status = RuntimeRunRequestStatus.RUNNING.value
        run_request.started_at = now
        await self.session.flush()
        runs = await MarketScanExecutor(self.session, settings=self.settings).run_due_scan_configs(
            workspace_id=run_request.workspace_id,
            limit=limit,
        )
        failed_count = sum(1 for item in runs if item.status == "failed")
        warning_count = sum(
            1 for item in runs if item.status in {"completed_with_warnings", "skipped"}
        )
        run_request.status = final_run_status(failed_count, warning_count)
        run_request.completed_at = utc_now()
        run_request.result_json = {
            "runCount": len(runs),
            "scanRunIds": [str(item.id) for item in runs],
            "failedCount": failed_count,
            "warningCount": warning_count,
        }


def build_worker_summary(
    definition: RuntimeWorkerDefinition,
    instances: list[RuntimeWorkerInstance],
    run_request_worker_counts: dict[str, dict[str, int]],
) -> RuntimeHealthWorkerSummary:
    worker_instances = [
        instance
        for instance in instances
        if instance.worker_definition_key == definition.key
    ]
    worker_counts = run_request_worker_counts.get(definition.key, {})
    return RuntimeHealthWorkerSummary(
        key=definition.key,
        name=definition.name,
        worker_type=definition.worker_type,
        definition_status=definition.status,
        enabled=definition.status == RuntimeWorkerDefinitionStatus.AVAILABLE.value,
        running_instances=count_instances(
            worker_instances,
            RuntimeWorkerInstanceStatus.RUNNING,
        ),
        stale_instances=count_instances(worker_instances, RuntimeWorkerInstanceStatus.STALE),
        last_heartbeat_at=max_heartbeat(worker_instances),
        pending_run_requests=worker_counts.get(RuntimeRunRequestStatus.PENDING.value, 0),
        running_run_requests=worker_counts.get(RuntimeRunRequestStatus.RUNNING.value, 0),
        failed_run_requests=worker_counts.get(RuntimeRunRequestStatus.FAILED.value, 0),
    )


def max_heartbeat(instances: list[RuntimeWorkerInstance]) -> datetime | None:
    heartbeats = [
        instance.last_heartbeat_at
        for instance in instances
        if instance.last_heartbeat_at is not None
    ]
    return max(heartbeats) if heartbeats else None


def count_instances(
    instances: list[RuntimeWorkerInstance],
    status: RuntimeWorkerInstanceStatus,
) -> int:
    return sum(1 for instance in instances if instance.status == status.value)


def count_definitions(
    definitions: list[RuntimeWorkerDefinition],
    status: RuntimeWorkerDefinitionStatus,
) -> int:
    return sum(1 for definition in definitions if definition.status == status.value)


def runtime_health_status(
    definitions: list[RuntimeWorkerDefinition],
    stale_instance_count: int,
    failed_run_request_count: int,
) -> str:
    if not definitions:
        return "unseeded"
    if stale_instance_count > 0 or failed_run_request_count > 0:
        return "degraded"
    return "healthy"


def final_run_status(failed_count: int, warning_count: int) -> str:
    if failed_count > 0 or warning_count > 0:
        return RuntimeRunRequestStatus.COMPLETED_WITH_WARNINGS.value
    return RuntimeRunRequestStatus.COMPLETED.value


def mark_unsupported(run_request: RuntimeWorkerRunRequest, now: datetime, reason: str) -> None:
    run_request.status = RuntimeRunRequestStatus.UNSUPPORTED.value
    run_request.started_at = now
    run_request.completed_at = now
    run_request.error_message = reason
    run_request.result_json = {
        "unsupported": True,
        "reason": reason,
    }


def bounded_limit(value: object, default: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(str(value))
    except ValueError:
        return default
    if parsed < 1:
        return default
    return min(parsed, maximum)
