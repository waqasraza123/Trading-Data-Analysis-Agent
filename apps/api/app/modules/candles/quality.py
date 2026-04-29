from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.core.schemas import ApiSchema
from app.modules.candles.timeframes import Timeframe, expected_timestamps, normalize_timestamp


class CandleQualityReport(ApiSchema):
    expected_candles: int = Field(ge=0)
    available_final_candles: int = Field(ge=0)
    available_partial_candles: int = Field(ge=0)
    missing_candles: int = Field(ge=0)
    duplicate_candles: int = Field(ge=0)
    quality_score: Decimal = Field(ge=0, le=1)
    has_partial_latest_candle: bool


class CandleQualityInput(ApiSchema):
    timestamp: datetime
    is_final: bool


def calculate_candle_quality(
    candles: list[CandleQualityInput],
    timeframe: Timeframe,
    start_time: datetime,
    end_time: datetime,
) -> CandleQualityReport:
    expected = expected_timestamps(start_time=start_time, end_time=end_time, timeframe=timeframe)
    expected_set = set(expected)
    final_timestamps = {
        normalize_timestamp(candle.timestamp)
        for candle in candles
        if candle.is_final and normalize_timestamp(candle.timestamp) in expected_set
    }
    partial_timestamps = {
        normalize_timestamp(candle.timestamp)
        for candle in candles
        if not candle.is_final and normalize_timestamp(candle.timestamp) in expected_set
    }
    all_timestamps = [normalize_timestamp(candle.timestamp) for candle in candles]
    duplicate_count = len(all_timestamps) - len(set(all_timestamps))
    missing_count = max(len(expected_set - final_timestamps), 0)
    quality_score = Decimal("1")
    if expected_set:
        quality_score = Decimal(len(final_timestamps)) / Decimal(len(expected_set))
    latest_expected = max(expected_set) if expected_set else None
    has_partial_latest_candle = (
        latest_expected in partial_timestamps if latest_expected else False
    )
    return CandleQualityReport(
        expected_candles=len(expected_set),
        available_final_candles=len(final_timestamps),
        available_partial_candles=len(partial_timestamps),
        missing_candles=missing_count,
        duplicate_candles=max(duplicate_count, 0),
        quality_score=quality_score.quantize(Decimal("0.00001")),
        has_partial_latest_candle=has_partial_latest_candle,
    )
