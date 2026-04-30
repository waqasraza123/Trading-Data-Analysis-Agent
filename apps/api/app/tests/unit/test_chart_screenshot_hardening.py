from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chart_screenshots.calibration import build_axis_calibration
from app.modules.chart_screenshots.models import ChartScreenshotRun, ChartScreenshotRunStatus
from app.modules.chart_screenshots.ocr import ChartOcrResult, OcrPoint, OcrTextBox
from app.modules.chart_screenshots.service import ChartScreenshotPredictionService
from app.modules.chart_screenshots.types import ChartOcrStatus


def test_axis_calibration_uses_ocr_price_axis_with_manual_window_start() -> None:
    result = ChartOcrResult(
        status=ChartOcrStatus.SUCCEEDED,
        provider="google_vision",
        confidence=Decimal("0.9100"),
        text_boxes=[
            text_box("1.1000", 380, 20, 410, 32),
            text_box("1.0900", 380, 160, 410, 172),
        ],
        provider_payload_json={"textAnnotations": []},
    )

    calibration = build_axis_calibration(
        ocr_result=result,
        image_width=420,
        image_height=220,
        manual_window_start=datetime(2026, 4, 30, 9, 0, tzinfo=UTC),
        manual_price_min=None,
        manual_price_max=None,
    )

    assert calibration.status == ChartOcrStatus.SUCCEEDED
    assert calibration.price_min == Decimal("1.0900")
    assert calibration.price_max == Decimal("1.1000")
    assert calibration.window_start == datetime(2026, 4, 30, 9, 0, tzinfo=UTC)


def test_axis_calibration_reports_partial_when_time_axis_missing() -> None:
    result = ChartOcrResult(
        status=ChartOcrStatus.SUCCEEDED,
        provider="google_vision",
        confidence=Decimal("0.9100"),
        text_boxes=[
            text_box("100", 380, 20, 410, 32),
            text_box("90", 380, 160, 410, 172),
        ],
        provider_payload_json={"textAnnotations": []},
    )

    calibration = build_axis_calibration(
        ocr_result=result,
        image_width=420,
        image_height=220,
        manual_window_start=None,
        manual_price_min=None,
        manual_price_max=None,
    )

    assert calibration.status == ChartOcrStatus.PARTIAL
    assert "OCR could not infer a complete time axis" in calibration.warnings


def test_finalize_run_marks_analysis_blocked_extraction_as_review_required() -> None:
    run = ChartScreenshotRun(
        id=uuid4(),
        workspace_id=uuid4(),
        source_id=uuid4(),
        symbol_id=uuid4(),
        timeframe="15m",
        parser_name="deterministic_png_candle_extraction",
        parser_version="0.1.0",
        status=ChartScreenshotRunStatus.PARSING.value,
        extraction_confidence=Decimal("0.5000"),
        raw_candle_count=3,
        stored_candle_count=3,
        duplicate_count=0,
        conflict_count=0,
        analysis_hypothesis="bullish",
        analysis_hypothesis_confidence=Decimal("0.5000"),
        extraction_warnings_json={"warnings": []},
        parser_metadata_json={"analysisBlockedReason": "low_extraction_confidence"},
    )
    service = ChartScreenshotPredictionService(cast(AsyncSession, object()))

    service.finalize_run(run)

    assert run.status == ChartScreenshotRunStatus.REVIEW_REQUIRED.value
    assert run.last_error_code == "chart_screenshot_review_required"


def text_box(text: str, left: int, top: int, right: int, bottom: int) -> OcrTextBox:
    return OcrTextBox(
        text=text,
        confidence=Decimal("0.9000"),
        vertices=[
            OcrPoint(left, top),
            OcrPoint(right, top),
            OcrPoint(right, bottom),
            OcrPoint(left, bottom),
        ],
    )
