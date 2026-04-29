from decimal import Decimal


def calculate_ema_series(values: list[Decimal], period: int) -> list[Decimal | None]:
    if period <= 0:
        return [None for _ in values]
    series: list[Decimal | None] = [None for _ in values]
    if len(values) < period:
        return series
    ema = sum(values[:period], Decimal("0")) / Decimal(period)
    series[period - 1] = ema
    multiplier = Decimal("2") / Decimal(period + 1)
    for index, value in enumerate(values[period:], start=period):
        ema = ((value - ema) * multiplier) + ema
        series[index] = ema
    return series


def latest_ema(values: list[Decimal], period: int) -> Decimal | None:
    ema_values = calculate_ema_series(values, period)
    for value in reversed(ema_values):
        if value is not None:
            return value
    return None


def ema_alignment(
    ema9: Decimal | None,
    ema21: Decimal | None,
    ema50: Decimal | None,
) -> str:
    if ema9 is None or ema21 is None or ema50 is None:
        return "unknown"
    if ema9 > ema21 > ema50:
        return "bullish_alignment"
    if ema9 < ema21 < ema50:
        return "bearish_alignment"
    return "mixed"
