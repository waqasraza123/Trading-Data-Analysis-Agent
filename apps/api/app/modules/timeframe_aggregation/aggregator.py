from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.core.errors import AppError
from app.modules.candles.models import Candle
from app.modules.candles.timeframes import Timeframe, normalize_timestamp, timeframe_duration


SUPPORTED_AGGREGATION_PAIRS: set[tuple[Timeframe, Timeframe]] = {
    (Timeframe.ONE_MINUTE, Timeframe.FIVE_MINUTES),
    (Timeframe.ONE_MINUTE, Timeframe.FIFTEEN_MINUTES),
    (Timeframe.ONE_MINUTE, Timeframe.THIRTY_MINUTES),
    (Timeframe.ONE_MINUTE, Timeframe.ONE_HOUR),
    (Timeframe.FIVE_MINUTES, Timeframe.FIFTEEN_MINUTES),
    (Timeframe.FIVE_MINUTES, Timeframe.THIRTY_MINUTES),
    (Timeframe.FIVE_MINUTES, Timeframe.ONE_HOUR),
    (Timeframe.FIFTEEN_MINUTES, Timeframe.ONE_HOUR),
    (Timeframe.ONE_HOUR, Timeframe.FOUR_HOURS),
}


@dataclass(frozen=True)
class AggregationWindow:
    derived_timestamp: datetime
    base_start_time: datetime
    base_end_time: datetime
    expected_base_count: int


@dataclass(frozen=True)
class DerivedCandleCandidate:
    window: AggregationWindow
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    actual_base_count: int
    completeness_score: Decimal


class TimeframeAggregator:
    def validate_pair(self, base_timeframe: Timeframe, target_timeframe: Timeframe) -> int:
        if (base_timeframe, target_timeframe) not in SUPPORTED_AGGREGATION_PAIRS:
            raise AppError(
                422,
                "unsupported_timeframe_aggregation",
                "Unsupported base and target timeframe pair",
            )
        base_seconds = int(timeframe_duration(base_timeframe).total_seconds())
        target_seconds = int(timeframe_duration(target_timeframe).total_seconds())
        if target_seconds <= base_seconds or target_seconds % base_seconds != 0:
            raise AppError(
                422,
                "invalid_timeframe_aggregation",
                "target_timeframe must be a clean multiple of base_timeframe",
            )
        return target_seconds // base_seconds

    def build_windows(
        self,
        base_timeframe: Timeframe,
        target_timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
    ) -> list[AggregationWindow]:
        expected_base_count = self.validate_pair(base_timeframe, target_timeframe)
        base_duration = timeframe_duration(base_timeframe)
        target_duration = timeframe_duration(target_timeframe)
        normalized_start = normalize_timestamp(start_time)
        normalized_end = normalize_timestamp(end_time)
        first_window = ceil_to_boundary(normalized_start, target_duration)
        last_base_start = normalized_end
        windows: list[AggregationWindow] = []
        current = first_window
        while current + target_duration - base_duration <= last_base_start:
            windows.append(
                AggregationWindow(
                    derived_timestamp=current,
                    base_start_time=current,
                    base_end_time=current + target_duration - base_duration,
                    expected_base_count=expected_base_count,
                )
            )
            current += target_duration
        return windows

    def aggregate_window(
        self,
        window: AggregationWindow,
        candles: list[Candle],
    ) -> DerivedCandleCandidate | None:
        window_candles = [
            candle
            for candle in candles
            if window.base_start_time <= normalize_timestamp(candle.timestamp) <= window.base_end_time
        ]
        by_timestamp = {
            normalize_timestamp(candle.timestamp): candle
            for candle in sorted(window_candles, key=lambda item: item.timestamp)
            if candle.is_final
        }
        actual_base_count = len(by_timestamp)
        if window.expected_base_count == 0:
            completeness_score = Decimal("0")
        else:
            completeness_score = Decimal(actual_base_count) / Decimal(window.expected_base_count)
        if actual_base_count != window.expected_base_count:
            return None
        ordered_candles = [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)]
        volume = self.sum_volume(ordered_candles)
        return DerivedCandleCandidate(
            window=window,
            open=ordered_candles[0].open,
            high=max(candle.high for candle in ordered_candles),
            low=min(candle.low for candle in ordered_candles),
            close=ordered_candles[-1].close,
            volume=volume,
            actual_base_count=actual_base_count,
            completeness_score=completeness_score.quantize(Decimal("0.00001")),
        )

    def completeness_score(self, expected_base_count: int, actual_base_count: int) -> Decimal:
        if expected_base_count == 0:
            return Decimal("0.00000")
        return (Decimal(actual_base_count) / Decimal(expected_base_count)).quantize(Decimal("0.00001"))

    def sum_volume(self, candles: list[Candle]) -> Decimal | None:
        if any(candle.volume is None for candle in candles):
            return None
        return sum((candle.volume for candle in candles if candle.volume is not None), Decimal("0"))


def floor_to_boundary(timestamp: datetime, duration: timedelta) -> datetime:
    normalized = normalize_timestamp(timestamp)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    seconds = int((normalized - epoch).total_seconds())
    duration_seconds = int(duration.total_seconds())
    floored_seconds = seconds - (seconds % duration_seconds)
    return epoch + timedelta(seconds=floored_seconds)


def ceil_to_boundary(timestamp: datetime, duration: timedelta) -> datetime:
    floored = floor_to_boundary(timestamp, duration)
    if floored == normalize_timestamp(timestamp):
        return floored
    return floored + duration
