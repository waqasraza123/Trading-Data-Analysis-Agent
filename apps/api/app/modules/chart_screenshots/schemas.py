from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.analysis.models import AnalysisRunStatus
from app.modules.analysis.schemas import AnalysisRunRead
from app.modules.candles.quality import CandleQualityReport
from app.modules.candles.schemas import CandleRead
from app.modules.candles.timeframes import Timeframe
from app.modules.chart_screenshots.models import (
    ChartScreenshotRunStatus,
    ChartTrendDirection,
)
from app.modules.signals.schemas import SignalClassificationRead


class ChartScreenshotCandle(ApiSchema):
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class ChartScreenshotPredictionCreate(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    source_id: UUID
    symbol_id: UUID
    timeframe: Timeframe
    file_name: str | None = Field(default=None, max_length=255)
    parser_source_path: str | None = Field(default=None, max_length=255)
    parser_name: str | None = Field(default=None, max_length=80)
    parser_version: str | None = Field(default=None, max_length=32)
    extraction_confidence: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    candles: list[ChartScreenshotCandle] = Field(min_length=3, max_length=1000)
    parser_metadata_json: dict[str, Any] = Field(default_factory=dict)
    trigger_analysis: bool = False
    include_news_correlation: bool = False
    include_ai_explanation: bool = False
    analysis_warmup_start_time: datetime | None = None
    analysis_baseline_start_time: datetime | None = None

    @field_validator("file_name", "parser_source_path", "parser_name", "parser_version")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ChartScreenshotReviewStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_CORRECTION = "needs_correction"
    CORRECTED = "corrected"


class ChartScreenshotRunReviewRequest(ApiSchema):
    review_status: ChartScreenshotReviewStatus
    reviewer_user_id: UUID | None = None
    review_notes: str | None = Field(default=None, max_length=1000)
    corrected_candles: list[ChartScreenshotCandle] | None = Field(
        default=None,
        min_length=3,
        max_length=1000,
    )
    trigger_analysis: bool = False
    include_news_correlation: bool = False
    include_ai_explanation: bool = False
    analysis_warmup_start_time: datetime | None = None
    analysis_baseline_start_time: datetime | None = None

    @field_validator("review_notes")
    @classmethod
    def normalize_review_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ChartScreenshotRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    source_id: UUID
    symbol_id: UUID
    analysis_run_id: UUID | None
    timeframe: str
    file_name: str | None
    parser_name: str
    parser_version: str
    parser_source_path: str | None
    status: ChartScreenshotRunStatus
    extraction_confidence: Decimal
    raw_candle_count: int
    stored_candle_count: int
    duplicate_count: int
    conflict_count: int
    analysis_hypothesis: ChartTrendDirection
    analysis_hypothesis_confidence: Decimal | None
    extracted_window_start: datetime | None
    extracted_window_end: datetime | None
    extracted_payload_json: dict[str, Any] | None
    extraction_warnings_json: dict[str, Any]
    parser_metadata_json: dict[str, Any]
    last_error_code: str | None
    last_error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class ChartScreenshotRunListRead(ApiSchema):
    count: int
    runs: list[ChartScreenshotRunRead]


class ChartScreenshotRunReviewRead(ApiSchema):
    reviewed_run: ChartScreenshotRunRead
    corrected_run: ChartScreenshotRunRead | None


class ChartScreenshotImageExtractionPreviewRead(ApiSchema):
    file_name: str | None
    parser_name: str
    parser_version: str
    timeframe: Timeframe
    window_start: datetime
    price_min: Decimal
    price_max: Decimal
    extraction_confidence: Decimal
    candles: list[ChartScreenshotCandle]
    analysis_hypothesis: ChartTrendDirection
    analysis_hypothesis_confidence: Decimal
    trend_metrics_json: dict[str, Any]
    warnings: list[str]
    requires_human_review: bool
    parser_metadata_json: dict[str, Any]


class ChartScreenshotDecisionRead(ApiSchema):
    chart_screenshot_run: ChartScreenshotRunRead
    decision_source: str
    direction: ChartTrendDirection
    confidence: Decimal | None
    confidence_label: str | None
    reasoning: list[str]
    warnings: list[str]
    limitations: list[str]
    analysis_status: AnalysisRunStatus | None
    analysis_run: AnalysisRunRead | None
    signal_classification: SignalClassificationRead | None


class ChartScreenshotReportRead(ApiSchema):
    chart_screenshot_run: ChartScreenshotRunRead
    stored_candles: list[CandleRead]
    candle_quality: CandleQualityReport | None
    decision: ChartScreenshotDecisionRead
    review_metadata_json: dict[str, Any] | None
    correction_run: ChartScreenshotRunRead | None
    corrected_from_run_id: UUID | None
    trend_metrics_json: dict[str, Any]
    parser_tuning_json: dict[str, Any] | None
    audit_warnings: list[str]
    report_limitations: list[str]


class ChartScreenshotLineageRead(ApiSchema):
    requested_run: ChartScreenshotRunRead
    root_run: ChartScreenshotRunRead
    parent_run: ChartScreenshotRunRead | None
    correction_runs: list[ChartScreenshotRunRead]
    latest_correction_run: ChartScreenshotRunRead | None
    recommended_run: ChartScreenshotRunRead
    recommended_decision: ChartScreenshotDecisionRead
    lineage_warnings: list[str]
