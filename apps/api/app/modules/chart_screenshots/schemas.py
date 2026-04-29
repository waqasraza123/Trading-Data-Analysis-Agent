from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.chart_screenshots.models import (
    ChartScreenshotRunStatus,
    ChartTrendDirection,
)


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

    @field_validator("file_name", "parser_source_path", "parser_name", "parser_version")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
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
