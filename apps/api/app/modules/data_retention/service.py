from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.data_retention.models import (
    DataRetentionPolicy,
    DataRetentionPolicyStatus,
    DataRetentionRun,
    DataRetentionRunItem,
    DataRetentionRunItemStatus,
    DataRetentionRunMode,
    DataRetentionRunStatus,
)
from app.modules.data_retention.planner import DataRetentionPlanner
from app.modules.data_retention.repository import DataRetentionRepository
from app.modules.data_retention.schemas import (
    DataRetentionPolicyCreate,
    DataRetentionPolicyDocument,
    DataRetentionPolicyUpdate,
    DataRetentionRunFilters,
)


class DataRetentionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DataRetentionRepository(session)
        self.planner = DataRetentionPlanner()

    async def create_policy(self, payload: DataRetentionPolicyCreate) -> DataRetentionPolicy:
        policy = DataRetentionPolicy(
            workspace_id=payload.workspace_id,
            name=payload.name,
            status=payload.status.value,
            policy_json=payload.policy_json.model_dump(by_alias=True),
        )
        created = await self.repository.create_policy(policy)
        await self.session.commit()
        return created

    async def list_policies(
        self,
        workspace_id: UUID,
        status: DataRetentionPolicyStatus | None,
        limit: int,
        offset: int,
    ) -> list[DataRetentionPolicy]:
        return await self.repository.list_policies(workspace_id, status, limit, offset)

    async def get_policy(self, policy_id: UUID) -> DataRetentionPolicy:
        policy = await self.repository.get_policy(policy_id)
        if policy is None:
            raise AppError(404, "data_retention_policy_not_found", "Data retention policy not found")
        return policy

    async def update_policy(
        self,
        policy_id: UUID,
        payload: DataRetentionPolicyUpdate,
    ) -> DataRetentionPolicy:
        policy = await self.get_policy(policy_id)
        if payload.name is not None:
            policy.name = payload.name
        if payload.status is not None:
            policy.status = payload.status.value
        if payload.policy_json is not None:
            policy.policy_json = payload.policy_json.model_dump(by_alias=True)
        updated = await self.repository.update_policy(policy)
        await self.session.commit()
        return updated

    async def plan_retention_run(self, filters: DataRetentionRunFilters) -> DataRetentionRun:
        policy_document = await self._resolve_policy(filters)
        target_types = set(filters.target_types) if filters.target_types else None
        target_plans = self.planner.build_target_plans(
            policy=policy_document,
            target_types=target_types,
            older_than=filters.older_than,
        )
        run = await self.repository.create_run(
            DataRetentionRun(
                workspace_id=filters.workspace_id,
                policy_id=filters.policy_id,
                mode=DataRetentionRunMode.DRY_RUN.value,
                status=DataRetentionRunStatus.PENDING.value,
                filters_json=filters.model_dump(mode="json", by_alias=True, exclude_none=True),
                summary={},
                result_json={},
            )
        )
        actions = await self.repository.plan_actions(
            workspace_id=filters.workspace_id,
            plans=target_plans,
            limit_per_target_type=filters.limit_per_target_type,
        )
        await self.repository.create_run_items(run.id, filters.workspace_id, actions)
        summary = self._build_plan_summary(actions)
        run.planned_action_count = len(actions)
        run.summary = summary
        run.result_json = {
            "dryRun": True,
            "applied": False,
            "policy": policy_document.model_dump(by_alias=True),
        }
        run.status = DataRetentionRunStatus.COMPLETED.value
        updated = await self.repository.update_run(run)
        await self.session.commit()
        return updated

    async def apply_retention_run(self, run_id: UUID) -> DataRetentionRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "data_retention_run_not_found", "Data retention run not found")
        if run.mode != DataRetentionRunMode.DRY_RUN.value:
            raise AppError(409, "retention_run_not_dry_run", "Only dry-run plans can be applied")
        if run.status not in {
            DataRetentionRunStatus.COMPLETED.value,
            DataRetentionRunStatus.COMPLETED_WITH_WARNINGS.value,
        }:
            raise AppError(409, "retention_run_not_ready", "Retention run is not ready to apply")
        items = await self.repository.list_planned_run_items(run.id)
        run.mode = DataRetentionRunMode.APPLY.value
        run.status = DataRetentionRunStatus.PENDING.value
        await self.repository.update_run(run)
        for item in items:
            try:
                await self.repository.apply_item(item)
            except Exception as error:
                item.status = DataRetentionRunItemStatus.FAILED.value
                item.metadata_json = {**item.metadata_json, "errorMessage": str(error)}
                await self.session.flush()
        counts = await self.repository.count_run_items_by_status(run.id)
        run.applied_action_count = counts.get(DataRetentionRunItemStatus.APPLIED.value, 0)
        run.skipped_action_count = counts.get(DataRetentionRunItemStatus.SKIPPED.value, 0)
        run.failed_action_count = counts.get(DataRetentionRunItemStatus.FAILED.value, 0)
        run.planned_action_count = sum(counts.values())
        run.status = (
            DataRetentionRunStatus.COMPLETED_WITH_WARNINGS.value
            if run.failed_action_count > 0 or run.skipped_action_count > 0
            else DataRetentionRunStatus.COMPLETED.value
        )
        run.result_json = {
            **run.result_json,
            "dryRun": False,
            "applied": True,
            "itemStatusCounts": counts,
        }
        updated = await self.repository.update_run(run)
        await self.session.commit()
        return updated

    async def get_run(self, run_id: UUID) -> DataRetentionRun:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(404, "data_retention_run_not_found", "Data retention run not found")
        return run

    async def list_run_items(
        self,
        run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[DataRetentionRunItem]:
        run = await self.get_run(run_id)
        return await self.repository.list_run_items(run.id, limit, offset)

    async def _resolve_policy(self, filters: DataRetentionRunFilters) -> DataRetentionPolicyDocument:
        if filters.policy_id is None:
            return DataRetentionPolicyDocument()
        policy = await self.get_policy(filters.policy_id)
        if policy.workspace_id != filters.workspace_id:
            raise AppError(
                404,
                "data_retention_policy_not_found",
                "Data retention policy not found for workspace",
            )
        if policy.status != DataRetentionPolicyStatus.ACTIVE.value:
            raise AppError(409, "data_retention_policy_inactive", "Data retention policy is not active")
        return DataRetentionPolicyDocument.model_validate(policy.policy_json)

    def _build_plan_summary(self, actions: list[object]) -> dict[str, object]:
        by_target_type: dict[str, int] = {}
        by_action_type: dict[str, int] = {}
        for action in actions:
            target_type = str(getattr(action, "target_type").value)
            action_type = str(getattr(action, "action_type").value)
            by_target_type[target_type] = by_target_type.get(target_type, 0) + 1
            by_action_type[action_type] = by_action_type.get(action_type, 0) + 1
        return {
            "totalPlannedActions": len(actions),
            "byTargetType": by_target_type,
            "byActionType": by_action_type,
            "dryRunOnly": True,
            "destructiveCleanupDefault": False,
        }
