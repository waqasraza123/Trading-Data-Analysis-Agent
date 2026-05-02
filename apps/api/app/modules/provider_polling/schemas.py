from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe, normalize_timestamp
from app.modules.provider_polling.models import ProviderPollingRequestStatus


class ProviderPollingProvider(StrEnum):
    MOCK_POLLING = "mock_polling"
    BINANCE_PUBLIC_REST = "binance_public_rest"
    GENERIC_OHLC_HTTP = "generic_ohlc_http"


class ProviderPollingRequestCreate(ApiSchema):
    workspace_id: UUID
    source_id: UUID
    symbol_id: UUID
    provider: ProviderPollingProvider
    provider_symbol: str = Field(min_length=1, max_length=80)
    timeframe: Timeframe
    start_time: datetime | None = None
    end_time: datetime | None = None
    limit: int | None = Field(default=None, ge=1)
    request_metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider_symbol")
    @classmethod
    def normalize_provider_symbol(cls, value: str) -> str:
        return value.strip()

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_optional_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return normalize_timestamp(value)

    @model_validator(mode="after")
    def validate_time_window(self) -> "ProviderPollingRequestCreate":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.start_time > self.end_time
        ):
            msg = "start_time must be before end_time"
            raise ValueError(msg)
        return self


class ProviderCandle(ApiSchema):
    provider_symbol: str = Field(min_length=1, max_length=80)
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)
    is_final: bool
    raw_item_json: dict[str, Any] | None = None

    @field_validator("provider_symbol")
    @classmethod
    def normalize_provider_symbol(cls, value: str) -> str:
        return value.strip()

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        return normalize_timestamp(value)

    @model_validator(mode="after")
    def validate_ohlc_relationship(self) -> "ProviderCandle":
        if self.high < self.open or self.high < self.close or self.high < self.low:
            msg = "high must be greater than or equal to open, close, and low"
            raise ValueError(msg)
        if self.low > self.open or self.low > self.close:
            msg = "low must be less than or equal to open and close"
            raise ValueError(msg)
        return self


class ProviderPollingWarning(ApiSchema):
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)


class ProviderPollingErrorItem(ApiSchema):
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=1000)
    raw_item_json: dict[str, Any] | None = None


class ProviderPollingRequestRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    source_id: UUID
    symbol_id: UUID
    provider: ProviderPollingProvider
    provider_symbol: str
    timeframe: str
    start_time: datetime | None
    end_time: datetime | None
    limit: int | None
    status: ProviderPollingRequestStatus
    requested_url: str | None
    request_metadata_json: dict[str, Any]
    response_metadata_json: dict[str, Any]
    received_candle_count: int
    stored_candle_count: int
    skipped_candle_count: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProviderPollingErrorRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    polling_request_id: UUID
    error_code: str
    error_message: str
    raw_item_json: dict[str, Any] | None
    created_at: datetime
