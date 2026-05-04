from dataclasses import dataclass
from datetime import UTC, datetime

from app.modules.candles.timeframes import Timeframe, timeframe_duration
from app.modules.market_memory.models import MarketMemoryFreshnessLabel


@dataclass(frozen=True)
class FreshnessThresholds:
    fresh_seconds_1m: int
    fresh_seconds_5m: int
    fresh_seconds_15m: int
    fresh_seconds_1h: int


def determine_freshness_label(
    latest_final_candle_time: datetime | None,
    timeframe: str,
    thresholds: FreshnessThresholds,
    now: datetime | None = None,
) -> MarketMemoryFreshnessLabel:
    if latest_final_candle_time is None:
        return MarketMemoryFreshnessLabel.NO_DATA
    normalized_now = normalize_datetime(now or datetime.now(UTC))
    normalized_candle_time = normalize_datetime(latest_final_candle_time)
    age_seconds = (normalized_now - normalized_candle_time).total_seconds()
    if age_seconds < 0:
        return MarketMemoryFreshnessLabel.FRESH
    threshold_seconds = freshness_threshold_seconds(timeframe, thresholds)
    if threshold_seconds <= 0:
        return MarketMemoryFreshnessLabel.UNKNOWN
    if age_seconds <= threshold_seconds:
        return MarketMemoryFreshnessLabel.FRESH
    if age_seconds <= threshold_seconds * 2:
        return MarketMemoryFreshnessLabel.DELAYED
    return MarketMemoryFreshnessLabel.STALE


def freshness_threshold_seconds(timeframe: str, thresholds: FreshnessThresholds) -> int:
    match timeframe:
        case Timeframe.ONE_MINUTE.value:
            return thresholds.fresh_seconds_1m
        case Timeframe.FIVE_MINUTES.value:
            return thresholds.fresh_seconds_5m
        case Timeframe.FIFTEEN_MINUTES.value:
            return thresholds.fresh_seconds_15m
        case Timeframe.ONE_HOUR.value:
            return thresholds.fresh_seconds_1h
        case _:
            try:
                return max(int(timeframe_duration(Timeframe(timeframe)).total_seconds() * 2), 1)
            except ValueError:
                return 0


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
