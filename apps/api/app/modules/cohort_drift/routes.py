from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.cohort_drift.models import CohortDriftLabel, CohortDriftSeverity
from app.modules.cohort_drift.schemas import (
    CohortDriftRecentResultsFilters,
    CohortDriftResultRead,
    CohortDriftRunRead,
    CohortDriftRunRequest,
)
from app.modules.cohort_drift.service import CohortDriftService
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(tags=["cohort-drift"])


def get_cohort_drift_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> CohortDriftService:
    return CohortDriftService(session)


@router.post(
    "/cohort-drift/run",
    response_model=CohortDriftRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
async def run_cohort_drift_detection(
    payload: CohortDriftRunRequest,
    service: Annotated[CohortDriftService, Depends(get_cohort_drift_service)],
) -> CohortDriftRunRead:
    run = await service.run_drift_detection(payload)
    return CohortDriftRunRead.model_validate(run)


@router.get("/cohort-drift/runs", response_model=list[CohortDriftRunRead])
async def list_cohort_drift_runs(
    service: Annotated[CohortDriftService, Depends(get_cohort_drift_service)],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: str | None = None,
) -> list[CohortDriftRunRead]:
    runs = await service.list_drift_runs(
        workspace_id=workspace_id,
        limit=limit,
        offset=offset,
        status=status,
    )
    return [CohortDriftRunRead.model_validate(run) for run in runs]


@router.get("/cohort-drift/runs/{run_id}", response_model=CohortDriftRunRead)
async def get_cohort_drift_run(
    run_id: UUID,
    service: Annotated[CohortDriftService, Depends(get_cohort_drift_service)],
) -> CohortDriftRunRead:
    run = await service.get_drift_run(run_id)
    return CohortDriftRunRead.model_validate(run)


@router.get(
    "/cohort-drift/runs/{run_id}/results",
    response_model=list[CohortDriftResultRead],
)
async def list_cohort_drift_results(
    run_id: UUID,
    service: Annotated[CohortDriftService, Depends(get_cohort_drift_service)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
    drift_label: CohortDriftLabel | None = None,
    severity: CohortDriftSeverity | None = None,
    horizon_minutes: Annotated[int | None, Query(gt=0)] = None,
    cohort_key: str | None = None,
) -> list[CohortDriftResultRead]:
    results = await service.list_drift_results(
        run_id=run_id,
        limit=limit,
        offset=offset,
        drift_label=drift_label.value if drift_label is not None else None,
        severity=severity.value if severity is not None else None,
        horizon_minutes=horizon_minutes,
        cohort_key=cohort_key,
    )
    return [CohortDriftResultRead.model_validate(result) for result in results]


@router.get("/cohort-drift/results/recent", response_model=list[CohortDriftResultRead])
async def list_recent_cohort_drift_results(
    service: Annotated[CohortDriftService, Depends(get_cohort_drift_service)],
    workspace_id: UUID,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    drift_label: CohortDriftLabel | None = None,
    severity: CohortDriftSeverity | None = None,
    horizon_minutes: Annotated[int | None, Query(gt=0)] = None,
    cohort_key: str | None = None,
) -> list[CohortDriftResultRead]:
    results = await service.list_recent_drift_results(
        workspace_id=workspace_id,
        filters=CohortDriftRecentResultsFilters(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            drift_label=drift_label,
            severity=severity,
            horizon_minutes=horizon_minutes,
            cohort_key=cohort_key,
        ),
    )
    return [CohortDriftResultRead.model_validate(result) for result in results]
