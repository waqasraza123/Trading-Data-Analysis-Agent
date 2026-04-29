from decimal import Decimal

from app.modules.candles.models import Candle


def calculate_volatility_features(
    analysis_candles: list[Candle],
    warmup_candles: list[Candle],
    baseline_candles: list[Candle],
) -> dict[str, object]:
    true_ranges = calculate_true_ranges(warmup_candles + analysis_candles)
    analysis_ranges = [candle.high - candle.low for candle in analysis_candles]
    baseline_ranges = [candle.high - candle.low for candle in baseline_candles]
    current_average_range = average(analysis_ranges)
    baseline_average_range = average(baseline_ranges)
    atr = average(true_ranges[-14:]) if true_ranges else current_average_range
    baseline_atr = average(calculate_true_ranges(baseline_candles)[-14:])
    expansion_ratio = safe_ratio(atr, baseline_atr or baseline_average_range)
    return {
        "trueRange": true_ranges[-1] if true_ranges else Decimal("0"),
        "currentAverageRange": current_average_range,
        "baselineAverageRange": baseline_average_range,
        "atr": atr,
        "baselineAtr": baseline_atr,
        "atrExpansionRatio": expansion_ratio,
        "volatilityState": volatility_state(expansion_ratio),
        "largeCandleCount": count_large_values(analysis_ranges, baseline_average_range),
    }


def calculate_true_ranges(candles: list[Candle]) -> list[Decimal]:
    true_ranges: list[Decimal] = []
    previous_close: Decimal | None = None
    for candle in candles:
        high_low = candle.high - candle.low
        if previous_close is None:
            true_ranges.append(high_low)
        else:
            true_ranges.append(
                max(
                    high_low,
                    abs(candle.high - previous_close),
                    abs(candle.low - previous_close),
                )
            )
        previous_close = candle.close
    return true_ranges


def average(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def volatility_state(expansion_ratio: Decimal) -> str:
    if expansion_ratio == 0:
        return "unknown"
    if expansion_ratio < Decimal("0.75"):
        return "compressed"
    if expansion_ratio <= Decimal("1.25"):
        return "normal"
    if expansion_ratio <= Decimal("2.00"):
        return "expanding"
    return "spike"


def count_large_values(values: list[Decimal], baseline: Decimal) -> int:
    if baseline == 0:
        return 0
    threshold = baseline * Decimal("1.5")
    return sum(1 for value in values if value >= threshold)
