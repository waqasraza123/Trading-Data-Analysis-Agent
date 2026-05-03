from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe, normalize_timestamp
from app.modules.market_scans.models import (
    MarketWatchlistStatus,
    ScheduledScanConfigStatus,
    ScheduledScanMode,
    ScheduledScanRunItemStatus,
    ScheduledScanRunStatus,
)


class WatchlistCreate(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "name must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WatchlistUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    status: MarketWatchlistStatus | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            msg = "name must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class WatchlistRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: MarketWatchlistStatus
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WatchlistItemCreate(ApiSchema):
    symbol_id: UUID
    source_id: UUID | None = None
    timeframe: Timeframe
    include_partial_live_candle: bool = False
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class WatchlistItemUpdate(ApiSchema):
    source_id: UUID | None = None
    timeframe: Timeframe | None = None
    include_partial_live_candle: bool | None = None
    is_active: bool | None = None
    metadata_json: dict[str, Any] | None = None


class WatchlistItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    watchlist_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    include_partial_live_candle: bool
    is_active: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScheduledScanConfigCreate(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    watchlist_id: UUID | None = None
    symbol_id: UUID | None = None
    source_id: UUID | None = None
    timeframe: Timeframe | None = None
    scan_mode: ScheduledScanMode
    lookback_minutes: int | None = Field(default=None, ge=1)
    interval_seconds: int | None = Field(default=None, ge=1)
    include_partial_live_candle: bool = False
    include_news_correlation: bool = False
    include_ai_explanation: bool = False
    include_reasoning: bool = False
    include_action_plan: bool = False
    next_run_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "name must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("next_run_at")
    @classmethod
    def normalize_next_run_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_timestamp(value)

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "ScheduledScanConfigCreate":
        if self.scan_mode == ScheduledScanMode.WATCHLIST and self.watchlist_id is None:
            msg = "watchlist_id is required for watchlist scan mode"
            raise ValueError(msg)
        if (
            self.scan_mode == ScheduledScanMode.SINGLE_SYMBOL
            and (self.symbol_id is None or self.timeframe is None)
        ):
            msg = "symbol_id and timeframe are required for single_symbol scan mode"
            raise ValueError(msg)
        return self


class ScheduledScanConfigUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    watchlist_id: UUID | None = None
    symbol_id: UUID | None = None
    source_id: UUID | None = None
    timeframe: Timeframe | None = None
    scan_mode: ScheduledScanMode | None = None
    lookback_minutes: int | None = Field(default=None, ge=1)
    interval_seconds: int | None = Field(default=None, ge=1)
    include_partial_live_candle: bool | None = None
    include_news_correlation: bool | None = None
    include_ai_explanation: bool | None = None
    include_reasoning: bool | None = None
    include_action_plan: bool | None = None
    status: ScheduledScanConfigStatus | None = None
    next_run_at: datetime | None = None
    metadata_json: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            msg = "name must not be blank"
            raise ValueError(msg)
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("next_run_at")
    @classmethod
    def normalize_next_run_at(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_timestamp(value)


class ScheduledScanConfigRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    watchlist_id: UUID | None
    symbol_id: UUID | None
    source_id: UUID | None
    timeframe: str | None
    scan_mode: ScheduledScanMode
    lookback_minutes: int
    interval_seconds: int
    include_partial_live_candle: bool
    include_news_correlation: bool
    include_ai_explanation: bool
    include_reasoning: bool
    include_action_plan: bool
    status: ScheduledScanConfigStatus
    last_run_at: datetime | None
    next_run_at: datetime | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScheduledScanRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    scan_config_id: UUID
    status: ScheduledScanRunStatus
    scan_mode: ScheduledScanMode
    scheduled_for: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    scanned_item_count: int
    analysis_run_count: int
    skipped_count: int
    failed_count: int
    analysis_run_ids_json: list[str]
    signal_ids_json: list[str]
    reasoning_run_ids_json: list[str] | None
    action_plan_ids_json: list[str] | None
    result_json: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ScheduledScanRunItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    scan_run_id: UUID
    scan_config_id: UUID
    watchlist_item_id: UUID | None
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    status: ScheduledScanRunItemStatus
    analysis_run_id: UUID | None
    signal_id: UUID | None
    reasoning_run_id: UUID | None
    action_plan_id: UUID | None
    skipped_reason: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class RunDueScansRequest(ApiSchema):
    workspace_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=500)


class RunDueScansResponse(ApiSchema):
    run_count: int
    runs: list[ScheduledScanRunRead]
