from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.daily_routines.models import (
    DailyRoutineRunStatus,
    DailyRoutineTemplateStatus,
    DailyRoutineType,
)
from app.modules.daily_routines.schemas import (
    DailyRoutineRunListFilters,
    DailyRoutineRunRead,
    DailyRoutineRunRequest,
    DailyRoutineRunStepRead,
    DailyRoutineSeedRead,
    DailyRoutineTemplateListFilters,
    DailyRoutineTemplateRead,
)
from app.modules.daily_routines.service import DailyRoutineService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/daily-routines", tags=["daily-routines"])


def get_daily_routine_service(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> DailyRoutineService:
    return DailyRoutineService(session=session, settings=request.app.state.settings)


@router.post(
    "/seed-default",
    response_model=DailyRoutineSeedRead,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission(Permission.RUNTIME_ADMIN))],
)
async def seed_default_daily_routine_templates(
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
) -> DailyRoutineSeedRead:
    templates = await service.seed_default_routine_templates()
    return DailyRoutineSeedRead(
        seeded_count=len(templates),
        templates=[DailyRoutineTemplateRead.model_validate(template) for template in templates],
    )


@router.get("/templates", response_model=list[DailyRoutineTemplateRead])
async def list_routine_templates(
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
    workspace_id: UUID | None = None,
    routine_type: DailyRoutineType | None = None,
    status_filter: Annotated[
        DailyRoutineTemplateStatus,
        Query(alias="status"),
    ] = DailyRoutineTemplateStatus.ACTIVE,
) -> list[DailyRoutineTemplateRead]:
    templates = await service.list_routine_templates(
        DailyRoutineTemplateListFilters(
            workspace_id=workspace_id,
            routine_type=routine_type,
            status=status_filter,
        )
    )
    return [DailyRoutineTemplateRead.model_validate(template) for template in templates]


@router.get("/templates/{template_id}", response_model=DailyRoutineTemplateRead)
async def get_routine_template(
    template_id: UUID,
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
    workspace_id: UUID | None = None,
) -> DailyRoutineTemplateRead:
    template = await service.get_routine_template(template_id, workspace_id=workspace_id)
    return DailyRoutineTemplateRead.model_validate(template)


@router.post(
    "/templates/{template_id}/run",
    response_model=DailyRoutineRunRead,
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def run_routine_template(
    template_id: UUID,
    payload: DailyRoutineRunRequest,
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
) -> DailyRoutineRunRead:
    run = await service.run_routine(template_id, payload)
    return DailyRoutineRunRead.model_validate(run)


@router.get("/runs", response_model=list[DailyRoutineRunRead])
async def list_routine_runs(
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
    workspace_id: UUID,
    template_id: UUID | None = None,
    status_filter: Annotated[DailyRoutineRunStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DailyRoutineRunRead]:
    runs = await service.list_routine_runs(
        DailyRoutineRunListFilters(
            workspace_id=workspace_id,
            template_id=template_id,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    )
    return [DailyRoutineRunRead.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=DailyRoutineRunRead)
async def get_routine_run(
    run_id: UUID,
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
) -> DailyRoutineRunRead:
    run = await service.get_routine_run(run_id)
    return DailyRoutineRunRead.model_validate(run)


@router.get("/runs/{run_id}/steps", response_model=list[DailyRoutineRunStepRead])
async def list_routine_run_steps(
    run_id: UUID,
    service: Annotated[DailyRoutineService, Depends(get_daily_routine_service)],
) -> list[DailyRoutineRunStepRead]:
    steps = await service.list_routine_run_steps(run_id)
    return [DailyRoutineRunStepRead.model_validate(step) for step in steps]
