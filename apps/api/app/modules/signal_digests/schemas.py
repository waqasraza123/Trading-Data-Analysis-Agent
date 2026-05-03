from datetime import date, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe
from app.modules.market_sessions.models import MarketSessionLabel
from app.modules.signal_digests.models import (
    SignalDigestItemType,
    SignalDigestPriority,
    SignalDigestStatus,
    SignalDigestType,
)


class SignalDigestFilters(ApiSchema):
    watchlist_id: UUID | None = None
    symbol_ids: list[UUID] = Field(default_factory=list)
    timeframes: list[Timeframe] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_filters(self) -> "SignalDigestFilters":
        self.symbol_ids = list(dict.fromkeys(self.symbol_ids))
        self.timeframes = list(dict.fromkeys(self.timeframes))
        return self


class SignalDigestCreate(ApiSchema):
    workspace_id: UUID
    digest_type: SignalDigestType
    period_start: datetime
    period_end: datetime
    timezone: str = "UTC"
    filters: SignalDigestFilters = Field(default_factory=SignalDigestFilters)
    max_items: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def validate_request(self) -> "SignalDigestCreate":
        if self.period_start >= self.period_end:
            msg = "period_start must be before period_end"
            raise ValueError(msg)
        self.timezone = validate_timezone_name(self.timezone)
        return self


class DailySignalDigestRequest(ApiSchema):
    workspace_id: UUID
    date: date
    timezone: str = "UTC"
    filters: SignalDigestFilters = Field(default_factory=SignalDigestFilters)
    max_items: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def validate_request(self) -> "DailySignalDigestRequest":
        self.timezone = validate_timezone_name(self.timezone)
        return self

    def to_create_request(self) -> SignalDigestCreate:
        timezone_info = ZoneInfo(self.timezone)
        period_start = datetime.combine(self.date, time.min, tzinfo=timezone_info)
        period_end = datetime.combine(self.date, time.max, tzinfo=timezone_info)
        return SignalDigestCreate(
            workspace_id=self.workspace_id,
            digest_type=SignalDigestType.DAILY,
            period_start=period_start,
            period_end=period_end,
            timezone=self.timezone,
            filters=self.filters,
            max_items=self.max_items,
        )


class SessionSignalDigestRequest(ApiSchema):
    workspace_id: UUID
    session_label: MarketSessionLabel
    date: date
    timezone: str = "UTC"
    filters: SignalDigestFilters = Field(default_factory=SignalDigestFilters)
    max_items: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def validate_request(self) -> "SessionSignalDigestRequest":
        self.timezone = validate_timezone_name(self.timezone)
        return self

    def to_create_request(self) -> SignalDigestCreate:
        timezone_info = ZoneInfo(self.timezone)
        period_start = datetime.combine(self.date, time.min, tzinfo=timezone_info)
        period_end = datetime.combine(self.date, time.max, tzinfo=timezone_info)
        filters_json = self.filters.model_copy()
        return SignalDigestCreate(
            workspace_id=self.workspace_id,
            digest_type=SignalDigestType.SESSION,
            period_start=period_start,
            period_end=period_end,
            timezone=self.timezone,
            filters=filters_json,
            max_items=self.max_items,
        )


class SignalDigestRunListFilters(ApiSchema):
    workspace_id: UUID
    digest_type: SignalDigestType | None = None
    status: SignalDigestStatus | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class SignalDigestRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    digest_type: SignalDigestType
    status: SignalDigestStatus
    digest_version: str
    title: str
    period_start: datetime
    period_end: datetime
    timezone: str
    filters_json: dict[str, Any]
    summary_json: dict[str, Any]
    section_counts_json: dict[str, int]
    warnings_json: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class SignalDigestItemRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    digest_run_id: UUID
    item_type: SignalDigestItemType
    symbol_id: UUID | None
    signal_id: UUID | None
    analysis_run_id: UUID | None
    outcome_id: UUID | None
    action_item_id: UUID | None
    news_event_id: UUID | None
    priority: SignalDigestPriority
    title: str
    summary: str
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
