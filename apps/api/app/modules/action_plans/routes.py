from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.action_plans.schemas import (
    ActionItemExecutionRead,
    ActionItemRead,
    ActionPlanCreateRequest,
    ActionPlanResponse,
    ExecuteDueActionItemsRequest,
    ExecuteDueActionItemsResponse,
    MarkDueActionItemsResponse,
    ReasoningActionWorkerStatusRead,
)
from app.modules.action_plans.service import ReasoningActionPlanService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["reasoning-action-plans"])


def get_action_plan_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ReasoningActionPlanService:
    return ReasoningActionPlanService(session)


@router.post(
    "/reasoning/runs/{reasoning_run_id}/action-plan",
    response_model=ActionPlanResponse,
    dependencies=[Depends(require_permission(Permission.ACTION_PLANS_WRITE))],
)
async def create_reasoning_action_plan(
    reasoning_run_id: UUID,
    payload: ActionPlanCreateRequest,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> ActionPlanResponse:
    return await service.create_from_reasoning_run(
        reasoning_run_id=reasoning_run_id,
        force_recompute=payload.force_recompute,
    )


@router.get(
    "/reasoning/runs/{reasoning_run_id}/action-plan",
    response_model=ActionPlanResponse,
)
async def get_reasoning_action_plan(
    reasoning_run_id: UUID,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> ActionPlanResponse:
    return await service.get_by_reasoning_run(reasoning_run_id)


@router.get("/action-plans/{action_plan_id}", response_model=ActionPlanResponse)
async def get_action_plan(
    action_plan_id: UUID,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> ActionPlanResponse:
    return await service.get_plan(action_plan_id)


@router.get("/action-plans/{action_plan_id}/items", response_model=list[ActionItemRead])
async def list_action_plan_items(
    action_plan_id: UUID,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> list[ActionItemRead]:
    return await service.list_plan_items(action_plan_id)


@router.post(
    "/action-items/execute-due",
    response_model=ExecuteDueActionItemsResponse,
    dependencies=[Depends(require_permission(Permission.ACTION_PLANS_WRITE))],
)
async def execute_due_action_items(
    payload: ExecuteDueActionItemsRequest,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> ExecuteDueActionItemsResponse:
    return await service.execute_due_actions(workspace_id=payload.workspace_id, limit=payload.limit)


@router.post(
    "/action-items/mark-due",
    response_model=MarkDueActionItemsResponse,
    dependencies=[Depends(require_permission(Permission.ACTION_PLANS_WRITE))],
)
async def mark_due_action_items(
    payload: ExecuteDueActionItemsRequest,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> MarkDueActionItemsResponse:
    return await service.mark_due_actions(workspace_id=payload.workspace_id)


@router.get("/action-items/due", response_model=list[ActionItemRead])
async def list_due_action_items(
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
    workspace_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[ActionItemRead]:
    return await service.list_due_actions(workspace_id=workspace_id, limit=limit)


@router.get("/action-items/worker/status", response_model=ReasoningActionWorkerStatusRead)
async def get_reasoning_action_worker_status(
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
    workspace_id: UUID | None = None,
) -> ReasoningActionWorkerStatusRead:
    return await service.worker_status(workspace_id=workspace_id)


@router.post(
    "/action-items/{action_item_id}/execute",
    response_model=ActionItemExecutionRead,
    dependencies=[Depends(require_permission(Permission.ACTION_PLANS_WRITE))],
)
async def execute_action_item(
    action_item_id: UUID,
    service: Annotated[ReasoningActionPlanService, Depends(get_action_plan_service)],
) -> ActionItemExecutionRead:
    return await service.execute_action_item(action_item_id)
