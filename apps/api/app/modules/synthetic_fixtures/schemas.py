from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiSchema
from app.modules.candles.timeframes import Timeframe, timestamp_aligns_with_timeframe


class SyntheticFixturePattern(StrEnum):
    BULLISH_BREAKOUT = "bullish_breakout"
    BEARISH_BREAKDOWN = "bearish_breakdown"
    BULLISH_CONTINUATION = "bullish_continuation"
    BEARISH_CONTINUATION = "bearish_continuation"
    BULLISH_REVERSAL = "bullish_reversal"
    BEARISH_REVERSAL = "bearish_reversal"
    FAKEOUT = "fakeout"
    SIDEWAYS_RANGE = "sideways_range"
    LOW_VOLATILITY_CHOP = "low_volatility_chop"
    HIGH_VOLATILITY_SPIKE = "high_volatility_spike"
    MISSING_CANDLE_GAP = "missing_candle_gap"
    JPY_PAIR_PIP_SAMPLE = "jpy_pair_pip_sample"
    CRYPTO_TICK_SAMPLE = "crypto_tick_sample"


class SyntheticFixtureOutputFormat(StrEnum):
    CANDLES = "candles"
    CSV = "csv"
    JSON_IMPORT_PAYLOAD = "json_import_payload"
    FULL = "full"


class SyntheticVolumeBehavior(StrEnum):
    NONE = "none"
    FLAT = "flat"
    TREND = "trend"
    VOLATILE = "volatile"


class SyntheticFixtureCandle(ApiSchema):
    timestamp: datetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal | None = Field(default=None, ge=0)


class SyntheticFixtureGenerateRequest(ApiSchema):
    pattern: SyntheticFixturePattern
    symbol: str = Field(default="EURUSD", min_length=1, max_length=40)
    timeframe: Timeframe = Timeframe.ONE_MINUTE
    start_time: datetime = Field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    candle_count: int = Field(default=40, ge=3, le=2000)
    start_price: Decimal = Field(default=Decimal("1.1000"), gt=0)
    volatility: Decimal = Field(default=Decimal("0.0005"), gt=0)
    volume_behavior: SyntheticVolumeBehavior = SyntheticVolumeBehavior.FLAT
    seed: int | None = None
    include_malformed: bool = False
    output_format: SyntheticFixtureOutputFormat = SyntheticFixtureOutputFormat.CANDLES
    workspace_id: UUID | None = None
    user_id: UUID | None = None
    source_id: UUID | None = None
    symbol_id: UUID | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            msg = "symbol must not be empty"
            raise ValueError(msg)
        return normalized

    @field_validator("start_time")
    @classmethod
    def normalize_start_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_aligned_start_time(self) -> "SyntheticFixtureGenerateRequest":
        if not timestamp_aligns_with_timeframe(self.start_time, self.timeframe):
            msg = "start_time must align with timeframe"
            raise ValueError(msg)
        return self


class SyntheticFixtureMetadata(ApiSchema):
    pattern: SyntheticFixturePattern
    symbol: str
    timeframe: Timeframe
    seed: int
    requested_candle_count: int
    generated_candle_count: int
    start_time: datetime
    end_time: datetime | None
    start_price: Decimal
    volatility: Decimal
    volume_behavior: SyntheticVolumeBehavior
    output_format: SyntheticFixtureOutputFormat
    malformed_indices: list[int]
    missing_timestamps: list[datetime]
    ohlc_valid: bool
    deterministic: bool = True
    production_data_mutated: bool = False
    external_data_used: bool = False


class SyntheticFixtureGenerateResponse(ApiSchema):
    symbol: str
    timeframe: Timeframe
    pattern: SyntheticFixturePattern
    candles: list[SyntheticFixtureCandle]
    csv_text: str | None = None
    json_import_payload: dict[str, Any] | None = None
    metadata: SyntheticFixtureMetadata
