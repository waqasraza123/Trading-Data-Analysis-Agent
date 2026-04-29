from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.news.models import (
    CorrelationLabel,
    DirectionAlignment,
    NewsEventType,
    NewsImportance,
    NewsSentiment,
    VolatilityReaction,
)


class NewsEventBase(ApiSchema):
    workspace_id: UUID | None = None
    source: str = Field(min_length=1, max_length=80)
    event_type: NewsEventType = NewsEventType.MANUAL
    title: str = Field(min_length=1, max_length=240)
    description: str | None = None
    event_time: datetime
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, max_length=16)
    asset: str | None = Field(default=None, max_length=32)
    symbol_id: UUID | None = None
    importance: NewsImportance = NewsImportance.UNKNOWN
    sentiment: NewsSentiment = NewsSentiment.UNKNOWN
    actual_value: str | None = Field(default=None, max_length=120)
    forecast_value: str | None = Field(default=None, max_length=120)
    previous_value: str | None = Field(default=None, max_length=120)
    impact_json: dict[str, Any] | None = None
    url: str | None = Field(default=None, max_length=1000)
    raw_payload_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def preserve_raw_payload(cls, data: object) -> object:
        if (
            isinstance(data, dict)
            and "rawPayloadJson" not in data
            and "raw_payload_json" not in data
        ):
            return {**data, "raw_payload_json": dict(data)}
        return data

    @field_validator("source", "title")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator(
        "description",
        "timezone",
        "actual_value",
        "forecast_value",
        "previous_value",
        "url",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("currency", "asset")
    @classmethod
    def normalize_symbol_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @field_validator("event_time")
    @classmethod
    def normalize_event_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class NewsEventCreate(NewsEventBase):
    pass


class NewsEventUpdate(ApiSchema):
    workspace_id: UUID | None = None
    source: str | None = Field(default=None, min_length=1, max_length=80)
    event_type: NewsEventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = None
    event_time: datetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    currency: str | None = Field(default=None, max_length=16)
    asset: str | None = Field(default=None, max_length=32)
    symbol_id: UUID | None = None
    importance: NewsImportance | None = None
    sentiment: NewsSentiment | None = None
    actual_value: str | None = Field(default=None, max_length=120)
    forecast_value: str | None = Field(default=None, max_length=120)
    previous_value: str | None = Field(default=None, max_length=120)
    impact_json: dict[str, Any] | None = None
    url: str | None = Field(default=None, max_length=1000)
    raw_payload_json: dict[str, Any] | None = None

    @field_validator("source", "title")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator(
        "description",
        "timezone",
        "actual_value",
        "forecast_value",
        "previous_value",
        "url",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("currency", "asset")
    @classmethod
    def normalize_symbol_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        return normalized or None

    @field_validator("event_time")
    @classmethod
    def normalize_event_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def reject_empty_update(self) -> "NewsEventUpdate":
        if not self.model_dump(exclude_unset=True):
            msg = "At least one update field is required"
            raise ValueError(msg)
        return self


class NewsEventImportRequest(ApiSchema):
    events: list[NewsEventCreate] = Field(min_length=1, max_length=1000)


class NewsEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    source: str
    event_type: NewsEventType
    title: str
    description: str | None
    event_time: datetime
    timezone: str | None
    currency: str | None
    asset: str | None
    symbol_id: UUID | None
    importance: NewsImportance
    sentiment: NewsSentiment
    actual_value: str | None
    forecast_value: str | None
    previous_value: str | None
    impact_json: dict[str, Any] | None
    url: str | None
    raw_payload_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NewsEventImportRead(ApiSchema):
    imported_count: int
    events: list[NewsEventRead]


class NewsCorrelationRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    analysis_run_id: UUID
    signal_id: UUID
    news_event_id: UUID
    correlation_score: Decimal
    correlation_label: CorrelationLabel
    time_delta_minutes: Decimal
    direction_alignment: DirectionAlignment
    volatility_reaction: VolatilityReaction
    relevance_score: Decimal
    importance_score: Decimal
    magnitude_score: Decimal
    sentiment_score: Decimal
    reason: str
    metadata_json: dict[str, Any]
    created_at: datetime


class NewsCorrelationRunRead(ApiSchema):
    analysis_run_id: UUID
    signal_id: UUID
    correlation_count: int
    correlations: list[NewsCorrelationRead]
