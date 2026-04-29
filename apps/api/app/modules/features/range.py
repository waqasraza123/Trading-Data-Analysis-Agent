from decimal import Decimal

from app.modules.candles.models import Candle


def calculate_range_features(
    analysis_candles: list[Candle],
    baseline_candles: list[Candle],
) -> dict[str, object]:
    current_range_high = max(candle.high for candle in analysis_candles)
    current_range_low = min(candle.low for candle in analysis_candles)
    previous_range_high = max((candle.high for candle in baseline_candles), default=None)
    previous_range_low = min((candle.low for candle in baseline_candles), default=None)
    last_close = analysis_candles[-1].close
    return {
        "previousRangeHigh": previous_range_high,
        "previousRangeLow": previous_range_low,
        "currentRangeHigh": current_range_high,
        "currentRangeLow": current_range_low,
        "candlesClosedAbovePreviousRange": count_closes_above(
            analysis_candles,
            previous_range_high,
        ),
        "candlesClosedBelowPreviousRange": count_closes_below(analysis_candles, previous_range_low),
        "distanceFromRangeHigh": distance(last_close, previous_range_high),
        "distanceFromRangeLow": distance(last_close, previous_range_low),
        "rangeState": range_state(last_close, previous_range_high, previous_range_low),
    }


def count_closes_above(candles: list[Candle], level: Decimal | None) -> int:
    if level is None:
        return 0
    return sum(1 for candle in candles if candle.close > level)


def count_closes_below(candles: list[Candle], level: Decimal | None) -> int:
    if level is None:
        return 0
    return sum(1 for candle in candles if candle.close < level)


def distance(price: Decimal, level: Decimal | None) -> Decimal | None:
    if level is None:
        return None
    return price - level


def range_state(
    last_close: Decimal,
    previous_range_high: Decimal | None,
    previous_range_low: Decimal | None,
) -> str:
    if previous_range_high is None or previous_range_low is None:
        return "no_baseline_range"
    if last_close > previous_range_high:
        return "above_previous_range"
    if last_close < previous_range_low:
        return "below_previous_range"
    return "inside_previous_range"
