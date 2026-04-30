from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.executor import ActionExecutionResult, ReasoningActionExecutor
from app.modules.action_plans.models import ReasoningActionItemStatus
from app.modules.action_plans.planner import ActionPlanBuildResult, ReasoningActionPlanner
from app.modules.action_plans.repository import ReasoningActionPlanRepository
from app.modules.action_plans.runner import ReasoningActionBatchResult, ReasoningActionRunner
from app.modules.action_plans.schemas import (
    ActionItemExecutionRead,
    ActionItemRead,
    ActionPlanRead,
    ActionPlanResponse,
    ExecuteDueActionItemsResponse,
    MarkDueActionItemsResponse,
    ReasoningActionWorkerRunRead,
    ReasoningActionWorkerStatusRead,
)


class ReasoningActionPlanService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = ReasoningActionPlanRepository(session)
        self.planner = ReasoningActionPlanner(session, settings=self.settings)
        self.executor = ReasoningActionExecutor(session, settings=self.settings)

    async def create_from_reasoning_run(
        self,
        reasoning_run_id: UUID,
        force_recompute: bool = False,
    ) -> ActionPlanResponse:
        result = await self.planner.build_plan_from_reasoning_run(
            reasoning_run_id=reasoning_run_id,
            force_recompute=force_recompute,
        )
        await self.session.commit()
        return response_from_build_result(result)

    async def get_by_reasoning_run(self, reasoning_run_id: UUID) -> ActionPlanResponse:
        plan = await self.repository.get_latest_by_reasoning_run_id(reasoning_run_id)
        if plan is None:
            raise AppError(404, "action_plan_not_found", "Action plan not found")
        items = await self.repository.list_items(plan.id)
        return ActionPlanResponse(
            plan=ActionPlanRead.model_validate(plan),
            items=[ActionItemRead.model_validate(item) for item in items],
            rejected_actions=metadata_list(plan.metadata_json, "rejectedActions"),
            skipped_actions=metadata_list(plan.metadata_json, "skippedActions"),
        )

    async def get_plan(self, action_plan_id: UUID) -> ActionPlanResponse:
        plan = await self.repository.get_plan(action_plan_id)
        if plan is None:
            raise AppError(404, "action_plan_not_found", "Action plan not found")
        items = await self.repository.list_items(plan.id)
        return ActionPlanResponse(
            plan=ActionPlanRead.model_validate(plan),
            items=[ActionItemRead.model_validate(item) for item in items],
            rejected_actions=metadata_list(plan.metadata_json, "rejectedActions"),
            skipped_actions=metadata_list(plan.metadata_json, "skippedActions"),
        )

    async def list_plan_items(self, action_plan_id: UUID) -> list[ActionItemRead]:
        plan = await self.repository.get_plan(action_plan_id)
        if plan is None:
            raise AppError(404, "action_plan_not_found", "Action plan not found")
        items = await self.repository.list_items(plan.id)
        return [ActionItemRead.model_validate(item) for item in items]

    async def execute_action_item(self, action_item_id: UUID) -> ActionItemExecutionRead:
        result = await self.executor.execute_action_item(action_item_id)
        return execution_read(result)

    async def execute_due_actions(
        self,
        workspace_id: UUID | None = None,
        limit: int = 100,
    ) -> ExecuteDueActionItemsResponse:
        result = await ReasoningActionRunner(
            session=self.session,
            settings=self.settings,
            worker_id="api-execute-due",
        ).execute_due_actions(workspace_id=workspace_id, limit=limit)
        return due_response(result)

    async def list_due_actions(
        self,
        workspace_id: UUID | None = None,
        limit: int = 100,
    ) -> list[ActionItemRead]:
        items = await self.executor.list_due_actions(workspace_id=workspace_id, limit=limit)
        return [ActionItemRead.model_validate(item) for item in items]

    async def mark_due_actions(
        self,
        workspace_id: UUID | None = None,
    ) -> MarkDueActionItemsResponse:
        items = await self.executor.mark_due_actions(workspace_id=workspace_id)
        return MarkDueActionItemsResponse(
            marked_count=len(items),
            items=[ActionItemRead.model_validate(item) for item in items],
        )

    async def worker_status(
        self,
        workspace_id: UUID | None = None,
    ) -> ReasoningActionWorkerStatusRead:
        now = utc_now()
        last_worker_run = await self.repository.get_latest_worker_run()
        return ReasoningActionWorkerStatusRead(
            pending_count=await self.repository.count_items_by_status(
                ReasoningActionItemStatus.PENDING,
                now=now,
                workspace_id=workspace_id,
            ),
            due_count=await self.repository.count_items_by_status(
                ReasoningActionItemStatus.DUE,
                now=now,
                workspace_id=workspace_id,
            ),
            running_count=await self.repository.count_items_by_status(
                ReasoningActionItemStatus.RUNNING,
                now=now,
                workspace_id=workspace_id,
            ),
            failed_count=await self.repository.count_items_by_status(
                ReasoningActionItemStatus.FAILED,
                now=now,
                workspace_id=workspace_id,
            ),
            oldest_due_at=await self.repository.oldest_due_at(now=now, workspace_id=workspace_id),
            worker_enabled=self.settings.reasoning_action_worker_enabled,
            last_worker_run=(
                ReasoningActionWorkerRunRead.model_validate(last_worker_run)
                if last_worker_run is not None
                else None
            ),
        )


def response_from_build_result(result: ActionPlanBuildResult) -> ActionPlanResponse:
    return ActionPlanResponse(
        plan=ActionPlanRead.model_validate(result.plan),
        items=[ActionItemRead.model_validate(item) for item in result.items],
        rejected_actions=result.rejected_actions,
        skipped_actions=result.skipped_actions,
    )


def execution_read(result: ActionExecutionResult) -> ActionItemExecutionRead:
    return ActionItemExecutionRead(
        item=ActionItemRead.model_validate(result.item),
        executed=result.executed,
        status=result.item.status,
        result=result.result,
    )


def due_response(result: ReasoningActionBatchResult) -> ExecuteDueActionItemsResponse:
    return ExecuteDueActionItemsResponse(
        executed_count=result.completed_count,
        skipped_count=result.skipped_count,
        failed_count=result.failed_count,
        items=[execution_read(item_result) for item_result in result.items],
    )


def metadata_list(metadata: dict[str, object], key: str) -> list[dict[str, object]]:
    value = metadata.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
