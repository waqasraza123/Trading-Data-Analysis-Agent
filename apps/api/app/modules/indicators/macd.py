from decimal import Decimal

from app.modules.indicators.ema import calculate_ema_series


def calculate_macd(values: list[Decimal]) -> dict[str, object]:
    ema12_values = calculate_ema_series(values, 12)
    ema26_values = calculate_ema_series(values, 26)
    macd_values: list[Decimal] = []
    for ema12, ema26 in zip(ema12_values, ema26_values, strict=True):
        if ema12 is not None and ema26 is not None:
            macd_values.append(ema12 - ema26)
    if not macd_values:
        return macd_payload(None, None, None)
    signal_values = calculate_ema_series(macd_values, 9)
    macd_value = macd_values[-1]
    signal_value = latest_non_null(signal_values)
    histogram = macd_value - signal_value if signal_value is not None else None
    return macd_payload(macd_value, signal_value, histogram)


def latest_non_null(values: list[Decimal | None]) -> Decimal | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def macd_payload(
    macd_value: Decimal | None,
    signal_value: Decimal | None,
    histogram: Decimal | None,
) -> dict[str, object]:
    return {
        "macd": macd_value,
        "signal": signal_value,
        "histogram": histogram,
        "state": macd_state(macd_value, signal_value, histogram),
        "isReady": macd_value is not None and signal_value is not None,
    }


def macd_state(
    macd_value: Decimal | None,
    signal_value: Decimal | None,
    histogram: Decimal | None,
) -> str:
    if macd_value is None or signal_value is None or histogram is None:
        return "unknown"
    if macd_value > signal_value and histogram > 0:
        return "bullish"
    if macd_value < signal_value and histogram < 0:
        return "bearish"
    return "neutral"
