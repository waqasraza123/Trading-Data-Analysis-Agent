from asyncio import to_thread
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.core.pagination import PaginationParams
from app.dependencies import database_session
from app.modules.candles.timeframes import Timeframe
from app.modules.chart_screenshots.calibration import AxisCalibration, build_axis_calibration
from app.modules.chart_screenshots.models import ChartScreenshotRunStatus
from app.modules.chart_screenshots.ocr import (
    ChartOcrResult,
    get_chart_ocr_provider,
    serialize_ocr_result,
)
from app.modules.chart_screenshots.parser import (
    CHART_SCREENSHOT_IMAGE_PARSER_NAME,
    CHART_SCREENSHOT_IMAGE_PARSER_VERSION,
    ChartImageBounds,
    ChartImageColorProfile,
    ChartImageExtractionConfig,
    ChartImageExtractionResult,
    ChartImageExtractionTuning,
    RgbPixel,
    build_trend_hypothesis,
    extract_candles_from_png,
    probe_image_dimensions,
)
from app.modules.chart_screenshots.schemas import (
    ChartScreenshotDecisionRead,
    ChartScreenshotImageExtractionPreviewRead,
    ChartScreenshotLineageRead,
    ChartScreenshotPredictionCreate,
    ChartScreenshotReportRead,
    ChartScreenshotRunListRead,
    ChartScreenshotRunRead,
    ChartScreenshotRunReviewRead,
    ChartScreenshotRunReviewRequest,
)
from app.modules.chart_screenshots.service import ChartScreenshotPredictionService
from app.modules.chart_screenshots.types import ChartCalibrationMode, ChartOcrStatus
from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission

router = APIRouter(prefix="/chart-screenshot-runs", tags=["chart-screenshot-runs"])
PREVIEW_HUMAN_REVIEW_CONFIDENCE_THRESHOLD = Decimal("0.7500")


@dataclass(frozen=True)
class ChartImageUploadExtraction:
    extraction: ChartImageExtractionResult
    window_start: datetime
    price_min: Decimal
    price_max: Decimal
    metadata_json: dict[str, object]
    warnings: list[str]
    ocr_status: ChartOcrStatus
    ocr_confidence: Decimal | None
    axis_calibration_json: dict[str, object] | None
    analysis_blocked_reason: str | None


def get_chart_screenshot_service(
    session: Annotated[AsyncSession, Depends(database_session)],
) -> ChartScreenshotPredictionService:
    return ChartScreenshotPredictionService(session)


@router.post(
    "",
    response_model=ChartScreenshotRunRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
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
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
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
    file: Annotated[UploadFile, File()],
    user_id: Annotated[UUID | None, Form()] = None,
    calibration_mode: Annotated[ChartCalibrationMode, Form()] = ChartCalibrationMode.MANUAL,
    window_start: Annotated[datetime | None, Form()] = None,
    price_min: Annotated[Decimal | None, Form(gt=0)] = None,
    price_max: Annotated[Decimal | None, Form(gt=0)] = None,
    chart_left: Annotated[int | None, Form(ge=0)] = None,
    chart_top: Annotated[int | None, Form(ge=0)] = None,
    chart_right: Annotated[int | None, Form(ge=0)] = None,
    chart_bottom: Annotated[int | None, Form(ge=0)] = None,
    foreground_distance_threshold: Annotated[int, Form(ge=1, le=765)] = 90,
    candle_color_delta_threshold: Annotated[int, Form(ge=0, le=255)] = 35,
    min_candle_channel: Annotated[int, Form(ge=0, le=255)] = 80,
    candle_blue_tolerance: Annotated[int, Form(ge=0, le=255)] = 20,
    active_column_min_pixels: Annotated[int, Form(ge=1, le=1000)] = 2,
    column_gap_tolerance: Annotated[int, Form(ge=0, le=1000)] = 3,
    min_cluster_width: Annotated[int, Form(ge=1, le=1000)] = 2,
    body_row_coverage_percent: Annotated[int, Form(ge=1, le=100)] = 50,
    max_detected_candles: Annotated[int, Form(ge=3, le=240)] = 240,
    bullish_color_hex: Annotated[str | None, Form(max_length=7)] = None,
    bearish_color_hex: Annotated[str | None, Form(max_length=7)] = None,
    color_profile_tolerance: Annotated[int, Form(ge=0, le=765)] = 80,
    trigger_analysis: Annotated[bool, Form()] = False,
    include_news_correlation: Annotated[bool, Form()] = False,
    include_ai_explanation: Annotated[bool, Form()] = False,
    analysis_warmup_start_time: Annotated[datetime | None, Form()] = None,
    analysis_baseline_start_time: Annotated[datetime | None, Form()] = None,
) -> ChartScreenshotRunRead:
    upload_extraction = await extract_chart_image_from_upload(
        request=request,
        file=file,
        calibration_mode=calibration_mode,
        timeframe=timeframe,
        window_start=window_start,
        price_min=price_min,
        price_max=price_max,
        chart_left=chart_left,
        chart_top=chart_top,
        chart_right=chart_right,
        chart_bottom=chart_bottom,
        tuning=build_chart_image_tuning(
            foreground_distance_threshold=foreground_distance_threshold,
            candle_color_delta_threshold=candle_color_delta_threshold,
            min_candle_channel=min_candle_channel,
            candle_blue_tolerance=candle_blue_tolerance,
            active_column_min_pixels=active_column_min_pixels,
            column_gap_tolerance=column_gap_tolerance,
            min_cluster_width=min_cluster_width,
            body_row_coverage_percent=body_row_coverage_percent,
            max_detected_candles=max_detected_candles,
            bullish_color_hex=bullish_color_hex,
            bearish_color_hex=bearish_color_hex,
            color_profile_tolerance=color_profile_tolerance,
        ),
    )
    if not upload_extraction.extraction.supported_for_analysis:
        raise AppError(
            422,
            "unsupported_chart_type",
            "Only candlestick and OHLC bar chart screenshots can be persisted for analysis",
        )
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
        extraction_confidence=upload_extraction.extraction.confidence,
        candles=upload_extraction.extraction.candles,
        parser_metadata_json=upload_extraction.metadata_json,
        analysis_blocked_reason=upload_extraction.analysis_blocked_reason,
        trigger_analysis=trigger_analysis,
        include_news_correlation=include_news_correlation,
        include_ai_explanation=include_ai_explanation,
        analysis_warmup_start_time=analysis_warmup_start_time,
        analysis_baseline_start_time=analysis_baseline_start_time,
    )
    run = await service.create_prediction_run(payload)
    return ChartScreenshotRunRead.model_validate(run)


@router.post("/image/preview", response_model=ChartScreenshotImageExtractionPreviewRead)
async def preview_chart_screenshot_image_extraction(
    request: Request,
    timeframe: Annotated[Timeframe, Form()],
    file: Annotated[UploadFile, File()],
    calibration_mode: Annotated[ChartCalibrationMode, Form()] = ChartCalibrationMode.MANUAL,
    window_start: Annotated[datetime | None, Form()] = None,
    price_min: Annotated[Decimal | None, Form(gt=0)] = None,
    price_max: Annotated[Decimal | None, Form(gt=0)] = None,
    chart_left: Annotated[int | None, Form(ge=0)] = None,
    chart_top: Annotated[int | None, Form(ge=0)] = None,
    chart_right: Annotated[int | None, Form(ge=0)] = None,
    chart_bottom: Annotated[int | None, Form(ge=0)] = None,
    foreground_distance_threshold: Annotated[int, Form(ge=1, le=765)] = 90,
    candle_color_delta_threshold: Annotated[int, Form(ge=0, le=255)] = 35,
    min_candle_channel: Annotated[int, Form(ge=0, le=255)] = 80,
    candle_blue_tolerance: Annotated[int, Form(ge=0, le=255)] = 20,
    active_column_min_pixels: Annotated[int, Form(ge=1, le=1000)] = 2,
    column_gap_tolerance: Annotated[int, Form(ge=0, le=1000)] = 3,
    min_cluster_width: Annotated[int, Form(ge=1, le=1000)] = 2,
    body_row_coverage_percent: Annotated[int, Form(ge=1, le=100)] = 50,
    max_detected_candles: Annotated[int, Form(ge=3, le=240)] = 240,
    bullish_color_hex: Annotated[str | None, Form(max_length=7)] = None,
    bearish_color_hex: Annotated[str | None, Form(max_length=7)] = None,
    color_profile_tolerance: Annotated[int, Form(ge=0, le=765)] = 80,
) -> ChartScreenshotImageExtractionPreviewRead:
    upload_extraction = await extract_chart_image_from_upload(
        request=request,
        file=file,
        calibration_mode=calibration_mode,
        timeframe=timeframe,
        window_start=window_start,
        price_min=price_min,
        price_max=price_max,
        chart_left=chart_left,
        chart_top=chart_top,
        chart_right=chart_right,
        chart_bottom=chart_bottom,
        tuning=build_chart_image_tuning(
            foreground_distance_threshold=foreground_distance_threshold,
            candle_color_delta_threshold=candle_color_delta_threshold,
            min_candle_channel=min_candle_channel,
            candle_blue_tolerance=candle_blue_tolerance,
            active_column_min_pixels=active_column_min_pixels,
            column_gap_tolerance=column_gap_tolerance,
            min_cluster_width=min_cluster_width,
            body_row_coverage_percent=body_row_coverage_percent,
            max_detected_candles=max_detected_candles,
            bullish_color_hex=bullish_color_hex,
            bearish_color_hex=bearish_color_hex,
            color_profile_tolerance=color_profile_tolerance,
        ),
    )
    extraction = upload_extraction.extraction
    hypothesis = build_trend_hypothesis(extraction.candles, extraction.confidence)
    warnings = [*upload_extraction.warnings, *hypothesis.warnings]
    return ChartScreenshotImageExtractionPreviewRead(
        file_name=file.filename,
        parser_name=CHART_SCREENSHOT_IMAGE_PARSER_NAME,
        parser_version=CHART_SCREENSHOT_IMAGE_PARSER_VERSION,
        timeframe=timeframe,
        window_start=upload_extraction.window_start,
        price_min=upload_extraction.price_min,
        price_max=upload_extraction.price_max,
        extraction_confidence=extraction.confidence,
        candles=extraction.candles,
        analysis_hypothesis=hypothesis.direction,
        analysis_hypothesis_confidence=hypothesis.confidence,
        trend_metrics_json=hypothesis.metrics_json,
        warnings=warnings,
        requires_human_review=(
            upload_extraction.analysis_blocked_reason is not None
            or extraction.confidence < PREVIEW_HUMAN_REVIEW_CONFIDENCE_THRESHOLD
            or bool(warnings)
        ),
        parser_metadata_json=upload_extraction.metadata_json,
        chart_type=extraction.chart_type,
        supported_for_analysis=extraction.supported_for_analysis,
        ocr_status=upload_extraction.ocr_status,
        ocr_confidence=upload_extraction.ocr_confidence,
        axis_calibration_json=upload_extraction.axis_calibration_json,
        analysis_blocked_reason=upload_extraction.analysis_blocked_reason,
    )


async def extract_chart_image_from_upload(
    request: Request,
    file: UploadFile,
    calibration_mode: ChartCalibrationMode,
    timeframe: Timeframe,
    window_start: datetime | None,
    price_min: Decimal | None,
    price_max: Decimal | None,
    chart_left: int | None,
    chart_top: int | None,
    chart_right: int | None,
    chart_bottom: int | None,
    tuning: ChartImageExtractionTuning,
) -> ChartImageUploadExtraction:
    file_bytes = await file.read()
    settings = request.app.state.settings
    if len(file_bytes) > settings.max_upload_file_bytes:
        raise AppError(413, "upload_file_too_large", "Upload file is too large")
    image_width, image_height = probe_image_dimensions(file_bytes)
    ocr_result = await extract_ocr_result(
        image_bytes=file_bytes,
        calibration_mode=calibration_mode,
        settings=settings,
    )
    axis_calibration = build_axis_calibration(
        ocr_result=ocr_result,
        image_width=image_width,
        image_height=image_height,
        manual_window_start=window_start,
        manual_price_min=price_min,
        manual_price_max=price_max,
    )
    resolved_window_start = axis_calibration.window_start
    resolved_price_min = axis_calibration.price_min
    resolved_price_max = axis_calibration.price_max
    validate_resolved_calibration(
        calibration_mode=calibration_mode,
        resolved_window_start=resolved_window_start,
        resolved_price_min=resolved_price_min,
        resolved_price_max=resolved_price_max,
        axis_calibration=axis_calibration,
    )
    assert resolved_window_start is not None
    assert resolved_price_min is not None
    assert resolved_price_max is not None
    if resolved_price_max <= resolved_price_min:
        raise AppError(422, "invalid_chart_price_range", "price_max must be greater than price_min")
    bounds = parse_chart_bounds(chart_left, chart_top, chart_right, chart_bottom)
    extraction = extract_candles_from_png(
        image_bytes=file_bytes,
        config=ChartImageExtractionConfig(
            timeframe=timeframe,
            window_start=resolved_window_start,
            price_min=resolved_price_min,
            price_max=resolved_price_max,
            bounds=bounds,
            tuning=tuning,
        ),
    )
    warnings = [*extraction.warnings, *axis_calibration.warnings]
    analysis_blocked_reason = determine_analysis_blocked_reason(
        extraction=extraction,
        axis_calibration=axis_calibration,
        settings=settings,
    )
    metadata = build_image_parser_metadata(
        extraction=extraction,
        axis_calibration=axis_calibration,
        ocr_result=ocr_result,
        calibration_mode=calibration_mode,
        analysis_blocked_reason=analysis_blocked_reason,
        warnings=warnings,
    )
    return ChartImageUploadExtraction(
        extraction=extraction,
        window_start=resolved_window_start,
        price_min=resolved_price_min,
        price_max=resolved_price_max,
        metadata_json=metadata,
        warnings=warnings,
        ocr_status=ocr_result.status if ocr_result is not None else ChartOcrStatus.NOT_REQUESTED,
        ocr_confidence=axis_calibration.confidence,
        axis_calibration_json=axis_calibration.metadata_json,
        analysis_blocked_reason=analysis_blocked_reason,
    )


async def extract_ocr_result(
    image_bytes: bytes,
    calibration_mode: ChartCalibrationMode,
    settings: Settings,
) -> ChartOcrResult | None:
    if calibration_mode == ChartCalibrationMode.MANUAL:
        return None
    if not settings.chart_ocr_enabled:
        if calibration_mode == ChartCalibrationMode.OCR:
            raise AppError(
                503,
                "chart_ocr_disabled",
                "Chart OCR is disabled for this environment",
            )
        return ChartOcrResult(
            status=ChartOcrStatus.DISABLED,
            provider=settings.chart_ocr_provider,
            confidence=None,
            text_boxes=[],
            provider_payload_json=None,
            warnings=["Chart OCR is disabled for this environment"],
        )
    provider = get_chart_ocr_provider(settings.chart_ocr_provider)
    return await to_thread(
        provider.extract_text,
        image_bytes,
        settings.chart_ocr_timeout_seconds,
    )


def validate_resolved_calibration(
    calibration_mode: ChartCalibrationMode,
    resolved_window_start: datetime | None,
    resolved_price_min: Decimal | None,
    resolved_price_max: Decimal | None,
    axis_calibration: AxisCalibration,
) -> None:
    if (
        resolved_window_start is not None
        and resolved_price_min is not None
        and resolved_price_max is not None
    ):
        return
    if calibration_mode == ChartCalibrationMode.MANUAL:
        raise AppError(
            422,
            "incomplete_manual_chart_calibration",
            "window_start, price_min, and price_max are required for manual calibration",
        )
    raise AppError(
        422,
        "chart_axis_calibration_incomplete",
        "; ".join(axis_calibration.warnings) or "Chart axis calibration is incomplete",
    )


def determine_analysis_blocked_reason(
    extraction: ChartImageExtractionResult,
    axis_calibration: AxisCalibration,
    settings: Settings,
) -> str | None:
    if not extraction.supported_for_analysis:
        return "unsupported_chart_type"
    if extraction.confidence < settings.chart_image_min_extraction_confidence:
        return "low_extraction_confidence"
    if axis_calibration.confidence is not None and (
        axis_calibration.confidence < settings.chart_ocr_min_confidence
    ):
        return "low_ocr_confidence"
    if axis_calibration.status == ChartOcrStatus.PARTIAL:
        return "axis_calibration_incomplete"
    return None


def build_image_parser_metadata(
    extraction: ChartImageExtractionResult,
    axis_calibration: AxisCalibration,
    ocr_result: ChartOcrResult | None,
    calibration_mode: ChartCalibrationMode,
    analysis_blocked_reason: str | None,
    warnings: list[str],
) -> dict[str, object]:
    metadata = {
        **extraction.parser_metadata_json,
        "calibrationMode": calibration_mode.value,
        "axisCalibration": axis_calibration.metadata_json,
        "ocr": (
            serialize_ocr_result(ocr_result)
            if ocr_result is not None
            else {
                "status": ChartOcrStatus.NOT_REQUESTED.value,
                "provider": None,
                "confidence": None,
                "textBoxes": [],
                "providerPayload": None,
                "warnings": [],
            }
        ),
    }
    if warnings:
        metadata["imageExtractionWarnings"] = warnings
    if analysis_blocked_reason is not None:
        metadata["analysisBlockedReason"] = analysis_blocked_reason
    return metadata


def build_chart_image_tuning(
    foreground_distance_threshold: int,
    candle_color_delta_threshold: int,
    min_candle_channel: int,
    candle_blue_tolerance: int,
    active_column_min_pixels: int,
    column_gap_tolerance: int,
    min_cluster_width: int,
    body_row_coverage_percent: int,
    max_detected_candles: int,
    bullish_color_hex: str | None,
    bearish_color_hex: str | None,
    color_profile_tolerance: int,
) -> ChartImageExtractionTuning:
    return ChartImageExtractionTuning(
        foreground_distance_threshold=foreground_distance_threshold,
        candle_color_delta_threshold=candle_color_delta_threshold,
        min_candle_channel=min_candle_channel,
        candle_blue_tolerance=candle_blue_tolerance,
        active_column_min_pixels=active_column_min_pixels,
        column_gap_tolerance=column_gap_tolerance,
        min_cluster_width=min_cluster_width,
        body_row_coverage_percent=body_row_coverage_percent,
        max_detected_candles=max_detected_candles,
        color_profile=ChartImageColorProfile(
            bullish=parse_rgb_hex_color(bullish_color_hex, "bullish_color_hex"),
            bearish=parse_rgb_hex_color(bearish_color_hex, "bearish_color_hex"),
            tolerance=color_profile_tolerance,
        ),
    )


def parse_rgb_hex_color(value: str | None, field_name: str) -> RgbPixel | None:
    if value is None or value.strip() == "":
        return None
    normalized = value.strip()
    if normalized.startswith("#"):
        normalized = normalized[1:]
    if len(normalized) != 6:
        raise AppError(422, "invalid_chart_color", f"{field_name} must be a 6-digit hex color")
    try:
        red = int(normalized[0:2], 16)
        green = int(normalized[2:4], 16)
        blue = int(normalized[4:6], 16)
    except ValueError as error:
        raise AppError(422, "invalid_chart_color", f"{field_name} must be a hex color") from error
    return RgbPixel(red=red, green=green, blue=blue)


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


@router.post(
    "/{run_id}/review",
    response_model=ChartScreenshotRunReviewRead,
    dependencies=[Depends(require_permission(Permission.ANALYSIS_WRITE))],
)
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


@router.get("/{run_id}/report", response_model=ChartScreenshotReportRead)
async def get_chart_screenshot_report(
    run_id: UUID,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
) -> ChartScreenshotReportRead:
    return await service.get_report(run_id)


@router.get("/{run_id}/lineage", response_model=ChartScreenshotLineageRead)
async def get_chart_screenshot_lineage(
    run_id: UUID,
    service: Annotated[
        ChartScreenshotPredictionService,
        Depends(get_chart_screenshot_service),
    ],
) -> ChartScreenshotLineageRead:
    return await service.get_lineage(run_id)
