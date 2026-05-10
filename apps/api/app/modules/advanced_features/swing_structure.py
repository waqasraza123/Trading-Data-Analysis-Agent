from decimal import Decimal

from app.modules.candles.models import Candle


def calculate_swing_structure(candles: list[Candle], swing_lookback: int) -> dict[str, object]:
    if len(candles) < (swing_lookback * 2) + 1:
        return {
            "swing_highs": [],
            "swing_lows": [],
            "higher_high_count": 0,
            "higher_low_count": 0,
            "lower_high_count": 0,
            "lower_low_count": 0,
            "structure_label": "unclear",
        }
    swing_highs = [
        swing_point(candles, index, "high", candles[index].high)
        for index in range(swing_lookback, len(candles) - swing_lookback)
        if is_swing_high(candles, index, swing_lookback)
    ]
    swing_lows = [
        swing_point(candles, index, "low", candles[index].low)
        for index in range(swing_lookback, len(candles) - swing_lookback)
        if is_swing_low(candles, index, swing_lookback)
    ]
    higher_high_count = count_higher(swing_highs)
    higher_low_count = count_higher(swing_lows)
    lower_high_count = count_lower(swing_highs)
    lower_low_count = count_lower(swing_lows)
    return {
        "swing_highs": swing_highs,
        "swing_lows": swing_lows,
        "higher_high_count": higher_high_count,
        "higher_low_count": higher_low_count,
        "lower_high_count": lower_high_count,
        "lower_low_count": lower_low_count,
        "structure_label": structure_label(
            higher_high_count=higher_high_count,
            higher_low_count=higher_low_count,
            lower_high_count=lower_high_count,
            lower_low_count=lower_low_count,
        ),
    }


def is_swing_high(candles: list[Candle], index: int, lookback: int) -> bool:
    current = candles[index].high
    window = candles[index - lookback : index + lookback + 1]
    return (
        current == max(candle.high for candle in window)
        and sum(1 for candle in window if candle.high == current) == 1
    )


def is_swing_low(candles: list[Candle], index: int, lookback: int) -> bool:
    current = candles[index].low
    window = candles[index - lookback : index + lookback + 1]
    return (
        current == min(candle.low for candle in window)
        and sum(1 for candle in window if candle.low == current) == 1
    )


def swing_point(
    candles: list[Candle],
    index: int,
    point_type: str,
    price: Decimal,
) -> dict[str, object]:
    return {
        "index": index,
        "timestamp": candles[index].timestamp.isoformat(),
        "type": point_type,
        "price": str(price),
    }


def count_higher(points: list[dict[str, object]]) -> int:
    count = 0
    for previous, current in zip(points, points[1:], strict=False):
        if Decimal(str(current["price"])) > Decimal(str(previous["price"])):
            count += 1
    return count


def count_lower(points: list[dict[str, object]]) -> int:
    count = 0
    for previous, current in zip(points, points[1:], strict=False):
        if Decimal(str(current["price"])) < Decimal(str(previous["price"])):
            count += 1
    return count


def structure_label(
    higher_high_count: int,
    higher_low_count: int,
    lower_high_count: int,
    lower_low_count: int,
) -> str:
    bullish_count = higher_high_count + higher_low_count
    bearish_count = lower_high_count + lower_low_count
    if bullish_count >= 2 and bullish_count > bearish_count:
        return "bullish_structure"
    if bearish_count >= 2 and bearish_count > bullish_count:
        return "bearish_structure"
    if bullish_count == 0 and bearish_count == 0:
        return "range_structure"
    if bullish_count == bearish_count:
        return "mixed"
    return "unclear"
