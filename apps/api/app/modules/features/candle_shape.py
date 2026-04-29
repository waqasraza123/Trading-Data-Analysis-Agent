from decimal import Decimal

from app.modules.candles.models import Candle


def calculate_candle_shape_features(candles: list[Candle]) -> dict[str, object]:
    body_sizes = [abs(candle.close - candle.open) for candle in candles]
    upper_wicks = [candle.high - max(candle.open, candle.close) for candle in candles]
    lower_wicks = [min(candle.open, candle.close) - candle.low for candle in candles]
    ranges = [candle.high - candle.low for candle in candles]
    average_body_size = average(body_sizes)
    average_upper_wick = average(upper_wicks)
    average_lower_wick = average(lower_wicks)
    average_range = average(ranges)
    return {
        "averageBodySize": average_body_size,
        "averageUpperWick": average_upper_wick,
        "averageLowerWick": average_lower_wick,
        "bodyToRangeRatio": safe_ratio(average_body_size, average_range),
        "upperWickRatio": safe_ratio(average_upper_wick, average_range),
        "lowerWickRatio": safe_ratio(average_lower_wick, average_range),
        "largeBodyCount": count_large_values(body_sizes, average_body_size),
        "largeWickCount": count_large_values(
            [upper + lower for upper, lower in zip(upper_wicks, lower_wicks, strict=True)],
            average_upper_wick + average_lower_wick,
        ),
        "indecisionCount": count_indecision_candles(body_sizes, ranges),
        "rejectionCount": count_rejection_candles(body_sizes, upper_wicks, lower_wicks),
    }


def average(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def count_large_values(values: list[Decimal], baseline: Decimal) -> int:
    if baseline == 0:
        return 0
    threshold = baseline * Decimal("1.5")
    return sum(1 for value in values if value >= threshold)


def count_indecision_candles(body_sizes: list[Decimal], ranges: list[Decimal]) -> int:
    return sum(
        1
        for body_size, candle_range in zip(body_sizes, ranges, strict=True)
        if candle_range > 0 and safe_ratio(body_size, candle_range) <= Decimal("0.25")
    )


def count_rejection_candles(
    body_sizes: list[Decimal],
    upper_wicks: list[Decimal],
    lower_wicks: list[Decimal],
) -> int:
    return sum(
        1
        for body_size, upper_wick, lower_wick in zip(
            body_sizes,
            upper_wicks,
            lower_wicks,
            strict=True,
        )
        if max(upper_wick, lower_wick) >= max(body_size * Decimal("2"), Decimal("0"))
        and max(upper_wick, lower_wick) > 0
    )
