from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.candles.timeframes import Timeframe
from app.modules.chart_screenshots.models import ChartScreenshotRunStatus
from app.modules.chart_screenshots.parser import (
    CHART_SCREENSHOT_IMAGE_PARSER_NAME,
    CHART_SCREENSHOT_IMAGE_PARSER_VERSION,
    ChartImageBounds,
    ChartImageExtractionConfig,
    extract_candles_from_png,
)
from app.modules.chart_screenshots.schemas import (
    ChartScreenshotDecisionRead,
    ChartScreenshotPredictionCreate,
    ChartScreenshotRunListRead,
    ChartScreenshotRunRead,
    ChartScreenshotRunReviewRead,
    ChartScreenshotRunReviewRequest,
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


@router.post(
    "/image",
    response_model=ChartScreenshotRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_chart_screenshot_run_from_image(
    request: Request,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
    workspace_id: Annotated[UUID, Form()],
    source_id: Annotated[UUID, Form()],
    symbol_id: Annotated[UUID, Form()],
    timeframe: Annotated[Timeframe, Form()],
    window_start: Annotated[datetime, Form()],
    price_min: Annotated[Decimal, Form(gt=0)],
    price_max: Annotated[Decimal, Form(gt=0)],
    file: Annotated[UploadFile, File()],
    user_id: Annotated[UUID | None, Form()] = None,
    chart_left: Annotated[int | None, Form(ge=0)] = None,
    chart_top: Annotated[int | None, Form(ge=0)] = None,
    chart_right: Annotated[int | None, Form(ge=0)] = None,
    chart_bottom: Annotated[int | None, Form(ge=0)] = None,
    trigger_analysis: Annotated[bool, Form()] = False,
    include_news_correlation: Annotated[bool, Form()] = False,
    include_ai_explanation: Annotated[bool, Form()] = False,
    analysis_warmup_start_time: Annotated[datetime | None, Form()] = None,
    analysis_baseline_start_time: Annotated[datetime | None, Form()] = None,
) -> ChartScreenshotRunRead:
    file_bytes = await file.read()
    settings = request.app.state.settings
    if len(file_bytes) > settings.max_upload_file_bytes:
        raise AppError(413, "upload_file_too_large", "Upload file is too large")
    if price_max <= price_min:
        raise AppError(422, "invalid_chart_price_range", "price_max must be greater than price_min")
    bounds = parse_chart_bounds(chart_left, chart_top, chart_right, chart_bottom)
    extraction = extract_candles_from_png(
        image_bytes=file_bytes,
        config=ChartImageExtractionConfig(
            timeframe=timeframe,
            window_start=window_start,
            price_min=price_min,
            price_max=price_max,
            bounds=bounds,
        ),
    )
    metadata = extraction.parser_metadata_json
    if extraction.warnings:
        metadata["imageExtractionWarnings"] = extraction.warnings
    payload = ChartScreenshotPredictionCreate(
        workspace_id=workspace_id,
        user_id=user_id,
        source_id=source_id,
        symbol_id=symbol_id,
        timeframe=timeframe,
        file_name=file.filename,
        parser_source_path=file.filename,
        parser_name=CHART_SCREENSHOT_IMAGE_PARSER_NAME,
        parser_version=CHART_SCREENSHOT_IMAGE_PARSER_VERSION,
        extraction_confidence=extraction.confidence,
        candles=extraction.candles,
        parser_metadata_json=metadata,
        trigger_analysis=trigger_analysis,
        include_news_correlation=include_news_correlation,
        include_ai_explanation=include_ai_explanation,
        analysis_warmup_start_time=analysis_warmup_start_time,
        analysis_baseline_start_time=analysis_baseline_start_time,
    )
    run = await service.create_prediction_run(payload)
    return ChartScreenshotRunRead.model_validate(run)


def parse_chart_bounds(
    left: int | None,
    top: int | None,
    right: int | None,
    bottom: int | None,
) -> ChartImageBounds | None:
    values = [left, top, right, bottom]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise AppError(
            422,
            "incomplete_chart_bounds",
            "chart_left, chart_top, chart_right, and chart_bottom must be provided together",
        )
    assert left is not None
    assert top is not None
    assert right is not None
    assert bottom is not None
    return ChartImageBounds(
        left=left,
        top=top,
        right=right,
        bottom=bottom,
    )


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


@router.post("/{run_id}/review", response_model=ChartScreenshotRunReviewRead)
async def review_chart_screenshot_run(
    run_id: UUID,
    payload: ChartScreenshotRunReviewRequest,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
) -> ChartScreenshotRunReviewRead:
    return await service.review_run(run_id, payload)


@router.get("/{run_id}/decision", response_model=ChartScreenshotDecisionRead)
async def get_chart_screenshot_decision(
    run_id: UUID,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
) -> ChartScreenshotDecisionRead:
    return await service.get_decision(run_id)
