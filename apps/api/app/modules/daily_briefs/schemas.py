from datetime import date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.daily_briefs.models import (
    DailyBriefItemType,
    DailyBriefPriority,
    DailyBriefStatus,
    DailyBriefType,
)
from app.modules.market_sessions.models import MarketSessionLabel


class DailyBriefFilters(ApiSchema):
    symbol_ids: list[UUID] = Field(default_factory=list)
    timeframes: list[Timeframe] = Field(default_factory=list)
    preference_profile_id: UUID | None = None

    @model_validator(mode="after")
    def normalize_filters(self) -> "DailyBriefFilters":
        self.symbol_ids = list(dict.fromkeys(self.symbol_ids))
        self.timeframes = list(dict.fromkeys(self.timeframes))
        return self


class DailyBriefCreate(ApiSchema):
    workspace_id: UUID
    brief_type: DailyBriefType = DailyBriefType.DAILY
    period_start: datetime
    period_end: datetime
    timezone: str = "UTC"
    watchlist_id: UUID | None = None
    filters: DailyBriefFilters = Field(default_factory=DailyBriefFilters)

    @model_validator(mode="after")
    def validate_request(self) -> "DailyBriefCreate":
        if self.period_start >= self.period_end:
            msg = "period_start must be before period_end"
            raise ValueError(msg)
        self.timezone = validate_timezone_name(self.timezone)
        return self


class DailyBriefDailyCreate(ApiSchema):
    workspace_id: UUID
    date: date
    timezone: str = "UTC"
    filters: DailyBriefFilters = Field(default_factory=DailyBriefFilters)

    @model_validator(mode="after")
    def validate_request(self) -> "DailyBriefDailyCreate":
        self.timezone = validate_timezone_name(self.timezone)
        return self

    def to_create_request(self) -> DailyBriefCreate:
        timezone_info = ZoneInfo(self.timezone)
        return DailyBriefCreate(
            workspace_id=self.workspace_id,
            brief_type=DailyBriefType.DAILY,
            period_start=datetime.combine(self.date, time.min, tzinfo=timezone_info),
            period_end=datetime.combine(self.date, time.max, tzinfo=timezone_info),
            timezone=self.timezone,
            filters=self.filters,
        )


class DailyBriefSessionCreate(ApiSchema):
    workspace_id: UUID
    session_label: MarketSessionLabel
    date: date
    timezone: str = "UTC"
    filters: DailyBriefFilters = Field(default_factory=DailyBriefFilters)

    @model_validator(mode="after")
    def validate_request(self) -> "DailyBriefSessionCreate":
        self.timezone = validate_timezone_name(self.timezone)
        return self

    def to_create_request(self) -> DailyBriefCreate:
        timezone_info = ZoneInfo(self.timezone)
        filters = self.filters.model_copy()
        return DailyBriefCreate(
            workspace_id=self.workspace_id,
            brief_type=DailyBriefType.SESSION,
            period_start=datetime.combine(self.date, time.min, tzinfo=timezone_info),
            period_end=datetime.combine(self.date, time.max, tzinfo=timezone_info),
            timezone=self.timezone,
            filters=filters,
        )


class DailyBriefWatchlistCreate(ApiSchema):
    workspace_id: UUID
    watchlist_id: UUID
    period_start: datetime
    period_end: datetime
    timezone: str = "UTC"
    filters: DailyBriefFilters = Field(default_factory=DailyBriefFilters)

    @model_validator(mode="after")
    def validate_request(self) -> "DailyBriefWatchlistCreate":
        if self.period_start >= self.period_end:
            msg = "period_start must be before period_end"
            raise ValueError(msg)
        self.timezone = validate_timezone_name(self.timezone)
        return self

    def to_create_request(self) -> DailyBriefCreate:
        return DailyBriefCreate(
            workspace_id=self.workspace_id,
            brief_type=DailyBriefType.WATCHLIST,
            period_start=self.period_start,
            period_end=self.period_end,
            timezone=self.timezone,
            watchlist_id=self.watchlist_id,
            filters=self.filters,
        )


class DailyBriefRunListFilters(ApiSchema):
    workspace_id: UUID
    brief_type: DailyBriefType | None = None
    status: DailyBriefStatus | None = None
    watchlist_id: UUID | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DailyBriefItemListFilters(ApiSchema):
    item_type: DailyBriefItemType | None = None
    priority: DailyBriefPriority | None = None
    limit: int = Field(default=150, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class DailyBriefRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    digest_id: UUID | None
    watchlist_id: UUID | None
    status: DailyBriefStatus
    brief_type: DailyBriefType
    brief_version: str
    period_start: datetime
    period_end: datetime
    timezone: str
    filters_json: dict[str, Any]
    summary_json: dict[str, Any]
    sections_json: dict[str, Any]
    warnings_json: list[dict[str, Any]]
    generated_at: datetime
    created_at: datetime
    updated_at: datetime


class DailyBriefItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    brief_run_id: UUID
    item_type: DailyBriefItemType
    priority: DailyBriefPriority
    symbol_id: UUID | None
    signal_id: UUID | None
    analysis_run_id: UUID | None
    outcome_id: UUID | None
    action_item_id: UUID | None
    setup_context_id: UUID | None
    source_type: str | None
    source_id: UUID | None
    title: str
    summary: str
    reason: str
    tags_json: list[str]
    metadata_json: dict[str, Any]
    sort_order: int
    created_at: datetime


def validate_timezone_name(value: str) -> str:
    normalized = value.strip() or "UTC"
    try:
        ZoneInfo(normalized)
    except ZoneInfoNotFoundError as error:
        msg = "timezone must be a valid IANA timezone"
        raise ValueError(msg) from error
    return normalized
