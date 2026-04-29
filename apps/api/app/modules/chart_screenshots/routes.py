from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.chart_screenshots.models import ChartScreenshotRunStatus
from app.modules.chart_screenshots.schemas import (
    ChartScreenshotPredictionCreate,
    ChartScreenshotRunListRead,
    ChartScreenshotRunRead,
)
from app.modules.chart_screenshots.service import ChartScreenshotPredictionService

router = APIRouter(prefix="/chart-screenshot-runs", tags=["chart-screenshot-runs"])


def get_chart_screenshot_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ChartScreenshotPredictionService:
    return ChartScreenshotPredictionService(session)


@router.post("", response_model=ChartScreenshotRunRead, status_code=status.HTTP_201_CREATED)
async def create_chart_screenshot_run(
    payload: ChartScreenshotPredictionCreate,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
) -> ChartScreenshotRunRead:
    run = await service.create_prediction_run(payload)
    return ChartScreenshotRunRead.model_validate(run)


@router.get("", response_model=ChartScreenshotRunListRead)
async def list_chart_screenshot_runs(
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    workspace_id: UUID | None = None,
    symbol_id: UUID | None = None,
    source_id: UUID | None = None,
    status: ChartScreenshotRunStatus | None = None,
) -> ChartScreenshotRunListRead:
    pagination = PaginationParams(limit=limit, offset=offset)
    runs = await service.list_runs(
        limit=pagination.limit,
        offset=pagination.offset,
        workspace_id=workspace_id,
        symbol_id=symbol_id,
        source_id=source_id,
        status=status,
    )
    return ChartScreenshotRunListRead(
        count=len(runs),
        runs=[ChartScreenshotRunRead.model_validate(run) for run in runs],
    )


@router.get("/{run_id}", response_model=ChartScreenshotRunRead)
async def get_chart_screenshot_run(
    run_id: UUID,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
) -> ChartScreenshotRunRead:
    run = await service.get_run(run_id)
    return ChartScreenshotRunRead.model_validate(run)
