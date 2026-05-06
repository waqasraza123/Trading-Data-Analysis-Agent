from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.daily_workflows.models import DailyWorkflowRunStatus, DailyWorkflowType
from app.modules.daily_workflows.schemas import (
    DailyWorkflowRunListFilters,
    DailyWorkflowRunRead,
    DailyWorkflowRunRequest,
    DailyWorkflowStepRead,
)
from app.modules.daily_workflows.service import DailyWorkflowService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/daily-workflows", tags=["daily-workflows"])


def get_daily_workflow_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DailyWorkflowService:
    return DailyWorkflowService(session=session, settings=request.app.state.settings)


@router.post(
    "/run",
    response_model=DailyWorkflowRunRead,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def run_daily_workflow(
    payload: DailyWorkflowRunRequest,
    service: Annotated[DailyWorkflowService, Depends(get_daily_workflow_service)],
) -> DailyWorkflowRunRead:
    run = await service.run_workflow(payload)
    return DailyWorkflowRunRead.model_validate(run)


@router.get("/runs", response_model=list[DailyWorkflowRunRead])
async def list_daily_workflow_runs(
    service: Annotated[DailyWorkflowService, Depends(get_daily_workflow_service)],
    workspace_id: UUID,
    workflow_type: DailyWorkflowType | None = None,
    status: DailyWorkflowRunStatus | None = None,
    watchlist_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DailyWorkflowRunRead]:
    runs = await service.list_runs(
        DailyWorkflowRunListFilters(
            workspace_id=workspace_id,
            workflow_type=workflow_type,
            status=status,
            watchlist_id=watchlist_id,
            limit=limit,
            offset=offset,
        )
    )
    return [DailyWorkflowRunRead.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=DailyWorkflowRunRead)
async def get_daily_workflow_run(
    run_id: UUID,
    service: Annotated[DailyWorkflowService, Depends(get_daily_workflow_service)],
) -> DailyWorkflowRunRead:
    run = await service.get_run(run_id)
    return DailyWorkflowRunRead.model_validate(run)


@router.get("/runs/{run_id}/steps", response_model=list[DailyWorkflowStepRead])
async def list_daily_workflow_steps(
    run_id: UUID,
    service: Annotated[DailyWorkflowService, Depends(get_daily_workflow_service)],
) -> list[DailyWorkflowStepRead]:
    steps = await service.list_steps(run_id)
    return [DailyWorkflowStepRead.model_validate(step) for step in steps]


@router.post(
    "/runs/{run_id}/cancel",
    response_model=DailyWorkflowRunRead,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def cancel_daily_workflow_run(
    run_id: UUID,
    service: Annotated[DailyWorkflowService, Depends(get_daily_workflow_service)],
) -> DailyWorkflowRunRead:
    run = await service.cancel_run(run_id)
    return DailyWorkflowRunRead.model_validate(run)
