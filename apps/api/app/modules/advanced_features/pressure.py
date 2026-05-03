from decimal import Decimal

from app.modules.candles.models import Candle

ZERO = Decimal("0")
ONE = Decimal("1")
FOUR_PLACES = Decimal("0.0001")


def calculate_wick_pressure(
    candles: list[Candle],
    wick_pressure_threshold: Decimal,
) -> dict[str, object]:
    if not candles:
        return {
            "upper_wick_pressure_score": "0.0000",
            "lower_wick_pressure_score": "0.0000",
            "rejection_direction": "none",
            "large_upper_wick_count": 0,
            "large_lower_wick_count": 0,
        }
    upper_ratios = [upper_wick_ratio(candle) for candle in candles]
    lower_ratios = [lower_wick_ratio(candle) for candle in candles]
    upper_score = average(upper_ratios)
    lower_score = average(lower_ratios)
    large_upper_count = sum(1 for ratio in upper_ratios if ratio >= wick_pressure_threshold)
    large_lower_count = sum(1 for ratio in lower_ratios if ratio >= wick_pressure_threshold)
    rejection_direction = resolve_rejection_direction(
        upper_score=upper_score,
        lower_score=lower_score,
        large_upper_count=large_upper_count,
        large_lower_count=large_lower_count,
    )
    return {
        "upper_wick_pressure_score": decimal_string(upper_score),
        "lower_wick_pressure_score": decimal_string(lower_score),
        "rejection_direction": rejection_direction,
        "large_upper_wick_count": large_upper_count,
        "large_lower_wick_count": large_lower_count,
    }


def upper_wick_ratio(candle: Candle) -> Decimal:
    candle_range = candle.high - candle.low
    if candle_range <= ZERO:
        return ZERO
    upper_wick = candle.high - max(candle.open, candle.close)
    return clamp(upper_wick / candle_range)


def lower_wick_ratio(candle: Candle) -> Decimal:
    candle_range = candle.high - candle.low
    if candle_range <= ZERO:
        return ZERO
    lower_wick = min(candle.open, candle.close) - candle.low
    return clamp(lower_wick / candle_range)


def resolve_rejection_direction(
    upper_score: Decimal,
    lower_score: Decimal,
    large_upper_count: int,
    large_lower_count: int,
) -> str:
    if large_upper_count == 0 and large_lower_count == 0:
        return "none"
    if large_upper_count > large_lower_count and upper_score > lower_score:
        return "bearish"
    if large_lower_count > large_upper_count and lower_score > upper_score:
        return "bullish"
    return "mixed"


def average(values: list[Decimal]) -> Decimal:
    if not values:
        return ZERO
    return clamp(sum(values, ZERO) / Decimal(len(values)))


def clamp(value: Decimal) -> Decimal:
    return max(ZERO, min(ONE, value))


def decimal_string(value: Decimal) -> str:
    return str(value.quantize(FOUR_PLACES))
