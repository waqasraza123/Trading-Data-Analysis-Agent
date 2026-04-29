from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.candles.timeframes import Timeframe, normalize_timestamp


class CandleOriginType(StrEnum):
    CSV_IMPORT = "csv_import"
    JSON_IMPORT = "json_import"
    LIVE_FEED = "live_feed"
    API_POLLING = "api_polling"
    MANUAL_SEED = "manual_seed"


class CandleUpsertStatus(StrEnum):
    INSERTED = "inserted"
    UPDATED_PARTIAL = "updated_partial"
    FINALIZED = "finalized"
    IGNORED_LATE_PARTIAL = "ignored_late_partial"
    DUPLICATE_FINAL = "duplicate_final"
    CONFLICTING_FINAL = "conflicting_final"


class CandleValidationCode(StrEnum):
    INVALID_TIMESTAMP = "invalid_timestamp"
    INVALID_TIMEFRAME = "invalid_timeframe"
    INVALID_OPEN = "invalid_open"
    INVALID_HIGH = "invalid_high"
    INVALID_LOW = "invalid_low"
    INVALID_CLOSE = "invalid_close"
    INVALID_VOLUME = "invalid_volume"
    INVALID_OHLC_RELATIONSHIP = "invalid_ohlc_relationship"
    INACTIVE_SYMBOL = "inactive_symbol"
    INACTIVE_SOURCE = "inactive_source"
    ORIGIN_REFERENCE_MISMATCH = "origin_reference_mismatch"


class NormalizedCandleInput(ApiSchema):
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID
    timeframe: Timeframe
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)
    is_final: bool
    origin_type: CandleOriginType
    origin_reference_id: UUID | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp_to_utc(cls, value: datetime) -> datetime:
        return normalize_timestamp(value)

    @model_validator(mode="after")
    def validate_ohlc_relationship(self) -> "NormalizedCandleInput":
        if self.high < self.open or self.high < self.close or self.high < self.low:
            msg = "high must be greater than or equal to open, close, and low"
            raise ValueError(msg)
        if self.low > self.open or self.low > self.close:
            msg = "low must be less than or equal to open and close"
            raise ValueError(msg)
        return self


class CandleValidationIssue(ApiSchema):
    code: CandleValidationCode
    message: str
    field_name: str | None = None


class CandleValidationResult(ApiSchema):
    is_valid: bool
    issues: list[CandleValidationIssue]


class CandleUpsertResult(ApiReadSchema):
    candle_id: UUID | None
    status: CandleUpsertStatus
    message: str


class CandleRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID
    import_batch_id: UUID | None
    live_feed_event_id: UUID | None
    timeframe: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    is_final: bool
    quality_score: Decimal | None
    created_at: datetime
    updated_at: datetime


class CandleCountRead(ApiSchema):
    count: int = Field(ge=0)
