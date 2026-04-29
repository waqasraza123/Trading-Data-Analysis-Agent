from decimal import Decimal

from app.modules.candles.models import Candle


def calculate_atr(candles: list[Candle], period: int = 14) -> Decimal | None:
    true_ranges = calculate_true_ranges(candles)
    if len(true_ranges) < period:
        return None
    return sum(true_ranges[-period:], Decimal("0")) / Decimal(period)


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


def atr_state(value: Decimal | None, baseline_value: Decimal | None) -> str:
    if value is None or baseline_value is None or baseline_value == 0:
        return "unknown"
    ratio = value / baseline_value
    if ratio < Decimal("0.75"):
        return "compressed"
    if ratio <= Decimal("1.25"):
        return "normal"
    if ratio <= Decimal("2.00"):
        return "expanding"
    return "spike"
