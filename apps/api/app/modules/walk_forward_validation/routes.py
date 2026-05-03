from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.walk_forward_validation.schemas import (
    WalkForwardValidationComparisonRead,
    WalkForwardValidationRunRead,
    WalkForwardValidationRunRequest,
    WalkForwardValidationWindowRead,
)
from app.modules.walk_forward_validation.service import WalkForwardValidationService

router = APIRouter(tags=["walk-forward-validations"])


def get_walk_forward_validation_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> WalkForwardValidationService:
    return WalkForwardValidationService(session)


@router.post(
    "/walk-forward-validations/run",
    response_model=WalkForwardValidationRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def run_walk_forward_validation(
    payload: WalkForwardValidationRunRequest,
    service: Annotated[
        WalkForwardValidationService,
        Depends(get_walk_forward_validation_service),
    ],
) -> WalkForwardValidationRunRead:
    run = await service.run_validation(payload)
    return WalkForwardValidationRunRead.model_validate(run)


@router.get(
    "/walk-forward-validations/runs",
    response_model=list[WalkForwardValidationRunRead],
)
async def list_walk_forward_validation_runs(
    service: Annotated[
        WalkForwardValidationService,
        Depends(get_walk_forward_validation_service),
    ],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: str | None = None,
) -> list[WalkForwardValidationRunRead]:
    runs = await service.list_runs(
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
        status=status,
    )
    return [WalkForwardValidationRunRead.model_validate(run) for run in runs]


@router.get(
    "/walk-forward-validations/runs/{run_id}",
    response_model=WalkForwardValidationRunRead,
)
async def get_walk_forward_validation_run(
    run_id: UUID,
    service: Annotated[
        WalkForwardValidationService,
        Depends(get_walk_forward_validation_service),
    ],
) -> WalkForwardValidationRunRead:
    run = await service.get_run(run_id)
    return WalkForwardValidationRunRead.model_validate(run)


@router.get(
    "/walk-forward-validations/runs/{run_id}/windows",
    response_model=list[WalkForwardValidationWindowRead],
)
async def list_walk_forward_validation_windows(
    run_id: UUID,
    service: Annotated[
        WalkForwardValidationService,
        Depends(get_walk_forward_validation_service),
    ],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
    horizon_minutes: Annotated[int | None, Query(gt=0)] = None,
    stability_label: str | None = None,
) -> list[WalkForwardValidationWindowRead]:
    windows = await service.list_windows(
        run_id=run_id,
        horizon_minutes=horizon_minutes,
        stability_label=stability_label,
        limit=limit,
        offset=offset,
    )
    return [WalkForwardValidationWindowRead.model_validate(window) for window in windows]


@router.get(
    "/walk-forward-validations/runs/{run_id}/comparisons",
    response_model=list[WalkForwardValidationComparisonRead],
)
async def list_walk_forward_validation_comparisons(
    run_id: UUID,
    service: Annotated[
        WalkForwardValidationService,
        Depends(get_walk_forward_validation_service),
    ],
) -> list[WalkForwardValidationComparisonRead]:
    comparisons = await service.list_comparisons(run_id)
    return [
        WalkForwardValidationComparisonRead.model_validate(comparison)
        for comparison in comparisons
    ]
