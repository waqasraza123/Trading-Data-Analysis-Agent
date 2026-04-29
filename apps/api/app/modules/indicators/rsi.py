from decimal import Decimal


def calculate_rsi(values: list[Decimal], period: int = 14) -> Decimal | None:
    if len(values) <= period:
        return None
    deltas = [
        current - previous
        for previous, current in zip(values, values[1:], strict=False)
    ]
    recent_deltas = deltas[-period:]
    gains = [delta if delta > 0 else Decimal("0") for delta in recent_deltas]
    losses = [abs(delta) if delta < 0 else Decimal("0") for delta in recent_deltas]
    average_gain = sum(gains, Decimal("0")) / Decimal(period)
    average_loss = sum(losses, Decimal("0")) / Decimal(period)
    if average_loss == 0 and average_gain == 0:
        return Decimal("50")
    if average_loss == 0:
        return Decimal("100")
    relative_strength = average_gain / average_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))


def rsi_state(value: Decimal | None) -> str:
    if value is None:
        return "unknown"
    if value < Decimal("30"):
        return "oversold"
    if value < Decimal("45"):
        return "bearish_momentum"
    if value <= Decimal("55"):
        return "neutral"
    if value <= Decimal("70"):
        return "bullish_momentum"
    return "overbought"
