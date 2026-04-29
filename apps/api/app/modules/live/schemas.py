from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.live.models import (
    LiveFeedEventProcessingStatus,
    LiveFeedEventType,
    LiveFeedSubscriptionStatus,
)


class LiveSubscriptionCreate(ApiSchema):
    workspace_id: UUID
    source_id: UUID
    symbol_id: UUID
    timeframe: Timeframe
    provider: str = Field(min_length=1, max_length=64)
    config_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()


class LiveSubscriptionUpdate(ApiSchema):
    source_id: UUID | None = None
    symbol_id: UUID | None = None
    timeframe: Timeframe | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    status: LiveFeedSubscriptionStatus | None = None
    config_json: dict[str, Any] | None = None

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class LiveSubscriptionRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_id: UUID
    symbol_id: UUID
    timeframe: str
    provider: str
    status: LiveFeedSubscriptionStatus
    last_message_at: datetime | None
    last_final_candle_at: datetime | None
    last_error: str | None
    config_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class LiveProviderMessage(ApiSchema):
    event_type: LiveFeedEventType
    provider_timestamp: datetime | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)


class NormalizedLiveProviderEvent(ApiSchema):
    event_type: LiveFeedEventType
    provider_timestamp: datetime | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    candle: RawCandlePayload | None = None
    error_message: str | None = None


class LiveFeedEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_id: UUID
    subscription_id: UUID | None
    provider: str
    event_type: LiveFeedEventType
    received_at: datetime
    provider_timestamp: datetime | None
    payload_json: dict[str, Any]
    processing_status: LiveFeedEventProcessingStatus
    error_message: str | None
    created_at: datetime


class LiveSubscriptionStaleCheckRequest(ApiSchema):
    workspace_id: UUID | None = None
    message_stale_after_seconds: int = Field(default=180, ge=1, le=86400)
    final_candle_stale_after_seconds: int = Field(default=300, ge=1, le=86400)


class LiveSubscriptionStaleCheckRead(ApiSchema):
    stale_count: int
