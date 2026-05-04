from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import database_session
from app.modules.pattern_attribution.schemas import (
    PatternAttributionResultRead,
    PatternAttributionRunRead,
    PatternAttributionRunRequest,
)
from app.modules.pattern_attribution.service import PatternAttributionService

router = APIRouter(prefix="/pattern-attribution", tags=["pattern-attribution"])


def get_pattern_attribution_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> PatternAttributionService:
    return PatternAttributionService(session)


@router.post(
    "/run",
    response_model=PatternAttributionRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def run_pattern_attribution(
    payload: PatternAttributionRunRequest,
    service: Annotated[PatternAttributionService, Depends(get_pattern_attribution_service)],
) -> PatternAttributionRunRead:
    run = await service.run_attribution(payload)
    return PatternAttributionRunRead.model_validate(run)


@router.get("/runs", response_model=list[PatternAttributionRunRead])
async def list_pattern_attribution_runs(
    service: Annotated[PatternAttributionService, Depends(get_pattern_attribution_service)],
    workspace_id: UUID,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PatternAttributionRunRead]:
    runs = await service.list_attribution_runs(
        workspace_id=workspace_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [PatternAttributionRunRead.model_validate(run) for run in runs]


@router.get("/runs/{run_id}", response_model=PatternAttributionRunRead)
async def get_pattern_attribution_run(
    run_id: UUID,
    service: Annotated[PatternAttributionService, Depends(get_pattern_attribution_service)],
) -> PatternAttributionRunRead:
    run = await service.get_attribution_run(run_id)
    return PatternAttributionRunRead.model_validate(run)


@router.get("/runs/{run_id}/results", response_model=list[PatternAttributionResultRead])
async def list_pattern_attribution_results(
    run_id: UUID,
    service: Annotated[PatternAttributionService, Depends(get_pattern_attribution_service)],
    attribution_label: str | None = None,
    pattern_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PatternAttributionResultRead]:
    results = await service.list_attribution_results(
        run_id=run_id,
        attribution_label=attribution_label,
        pattern_type=pattern_type,
        limit=limit,
        offset=offset,
    )
    return [PatternAttributionResultRead.model_validate(result) for result in results]
