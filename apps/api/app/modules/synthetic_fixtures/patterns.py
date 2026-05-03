from dataclasses import dataclass
from decimal import Decimal

from app.modules.synthetic_fixtures.schemas import SyntheticFixturePattern


@dataclass(frozen=True)
class CandleShape:
    move: Decimal
    upper_wick: Decimal
    lower_wick: Decimal
    volume_multiplier: Decimal = Decimal("1")


def shapes_for_pattern(
    pattern: SyntheticFixturePattern,
    candle_count: int,
    volatility: Decimal,
) -> list[CandleShape]:
    match pattern:
        case SyntheticFixturePattern.BULLISH_BREAKOUT:
            return generate_bullish_breakout(candle_count, volatility)
        case SyntheticFixturePattern.BEARISH_BREAKDOWN:
            return generate_bearish_breakdown(candle_count, volatility)
        case SyntheticFixturePattern.BULLISH_CONTINUATION:
            return generate_bullish_continuation(candle_count, volatility)
        case SyntheticFixturePattern.BEARISH_CONTINUATION:
            return generate_bearish_continuation(candle_count, volatility)
        case SyntheticFixturePattern.BULLISH_REVERSAL:
            return generate_bullish_reversal(candle_count, volatility)
        case SyntheticFixturePattern.BEARISH_REVERSAL:
            return generate_bearish_reversal(candle_count, volatility)
        case SyntheticFixturePattern.FAKEOUT:
            return generate_fakeout(candle_count, volatility)
        case SyntheticFixturePattern.SIDEWAYS_RANGE:
            return generate_sideways_range(candle_count, volatility)
        case SyntheticFixturePattern.LOW_VOLATILITY_CHOP:
            return generate_low_volatility_chop(candle_count, volatility)
        case SyntheticFixturePattern.HIGH_VOLATILITY_SPIKE:
            return generate_high_volatility_spike(candle_count, volatility)
        case SyntheticFixturePattern.MISSING_CANDLE_GAP:
            return generate_missing_candle_gap(candle_count, volatility)
        case SyntheticFixturePattern.JPY_PAIR_PIP_SAMPLE:
            return generate_jpy_pair_pip_sample(candle_count, volatility)
        case SyntheticFixturePattern.CRYPTO_TICK_SAMPLE:
            return generate_crypto_tick_sample(candle_count, volatility)
    msg = f"Unsupported synthetic fixture pattern: {pattern}"
    raise ValueError(msg)


def generate_bullish_breakout(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    base = alternating_range(candle_count // 2, volatility * Decimal("0.20"))
    lift = directional_shapes(candle_count - len(base), volatility, Decimal("1"))
    if lift:
        lift[-1] = CandleShape(
            volatility * Decimal("2.40"),
            volatility * Decimal("0.55"),
            volatility * Decimal("0.25"),
            Decimal("1.80"),
        )
    return fit_count([*base, *lift], candle_count)


def generate_bearish_breakdown(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    base = alternating_range(candle_count // 2, volatility * Decimal("0.20"))
    drop = directional_shapes(candle_count - len(base), volatility, Decimal("-1"))
    if drop:
        drop[-1] = CandleShape(
            volatility * Decimal("-2.40"),
            volatility * Decimal("0.25"),
            volatility * Decimal("0.55"),
            Decimal("1.80"),
        )
    return fit_count([*base, *drop], candle_count)


def generate_bullish_continuation(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    first = directional_shapes(max(2, candle_count // 3), volatility, Decimal("1"))
    pullback = directional_shapes(
        max(1, candle_count // 4),
        volatility * Decimal("0.45"),
        Decimal("-1"),
    )
    resume = directional_shapes(
        candle_count - len(first) - len(pullback),
        volatility * Decimal("1.20"),
        Decimal("1"),
    )
    return fit_count([*first, *pullback, *resume], candle_count)


def generate_bearish_continuation(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    first = directional_shapes(max(2, candle_count // 3), volatility, Decimal("-1"))
    pullback = directional_shapes(
        max(1, candle_count // 4),
        volatility * Decimal("0.45"),
        Decimal("1"),
    )
    resume = directional_shapes(
        candle_count - len(first) - len(pullback),
        volatility * Decimal("1.20"),
        Decimal("-1"),
    )
    return fit_count([*first, *pullback, *resume], candle_count)


def generate_bullish_reversal(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    decline = directional_shapes(max(2, candle_count // 2), volatility, Decimal("-1"))
    basing = alternating_range(max(1, candle_count // 5), volatility * Decimal("0.25"))
    reversal = directional_shapes(
        candle_count - len(decline) - len(basing),
        volatility * Decimal("1.10"),
        Decimal("1"),
    )
    if reversal:
        reversal[-1] = CandleShape(
            volatility * Decimal("1.70"),
            volatility * Decimal("0.35"),
            volatility * Decimal("2.80"),
            Decimal("1.65"),
        )
    return fit_count([*decline, *basing, *reversal], candle_count)


def generate_bearish_reversal(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    advance = directional_shapes(max(2, candle_count // 2), volatility, Decimal("1"))
    basing = alternating_range(max(1, candle_count // 5), volatility * Decimal("0.25"))
    reversal = directional_shapes(
        candle_count - len(advance) - len(basing),
        volatility * Decimal("1.10"),
        Decimal("-1"),
    )
    if reversal:
        reversal[-1] = CandleShape(
            volatility * Decimal("-1.70"),
            volatility * Decimal("2.80"),
            volatility * Decimal("0.35"),
            Decimal("1.65"),
        )
    return fit_count([*advance, *basing, *reversal], candle_count)


def generate_fakeout(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    base = alternating_range(max(3, candle_count - 3), volatility * Decimal("0.25"))
    fakeout = [
        CandleShape(
            volatility * Decimal("1.70"),
            volatility * Decimal("1.40"),
            volatility * Decimal("0.30"),
            Decimal("1.70"),
        ),
        CandleShape(
            volatility * Decimal("-1.95"),
            volatility * Decimal("2.60"),
            volatility * Decimal("0.35"),
            Decimal("1.90"),
        ),
        CandleShape(
            volatility * Decimal("-0.20"),
            volatility * Decimal("0.45"),
            volatility * Decimal("0.45"),
            Decimal("1.20"),
        ),
    ]
    return fit_count([*base, *fakeout], candle_count)


def generate_sideways_range(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    return fit_count(alternating_range(candle_count, volatility * Decimal("0.45")), candle_count)


def generate_low_volatility_chop(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    return fit_count(alternating_range(candle_count, volatility * Decimal("0.12")), candle_count)


def generate_high_volatility_spike(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    shapes = alternating_range(candle_count, volatility * Decimal("0.35"))
    midpoint = max(1, candle_count // 2)
    shapes[midpoint] = CandleShape(
        volatility * Decimal("4.50"),
        volatility * Decimal("5.00"),
        volatility * Decimal("4.00"),
        Decimal("3.50"),
    )
    if midpoint + 1 < candle_count:
        shapes[midpoint + 1] = CandleShape(
            volatility * Decimal("-3.20"),
            volatility * Decimal("2.50"),
            volatility * Decimal("3.00"),
            Decimal("2.80"),
        )
    return fit_count(shapes, candle_count)


def generate_missing_candle_gap(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    return generate_sideways_range(candle_count, volatility)


def generate_jpy_pair_pip_sample(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    pip = max(volatility, Decimal("0.010"))
    return fit_count(
        [
            CandleShape(
                pip * Decimal("1.0"),
                pip * Decimal("0.8"),
                pip * Decimal("0.4"),
                Decimal("1.0"),
            ),
            CandleShape(
                pip * Decimal("-0.5"),
                pip * Decimal("0.5"),
                pip * Decimal("0.7"),
                Decimal("1.0"),
            ),
            CandleShape(
                pip * Decimal("1.5"),
                pip * Decimal("1.0"),
                pip * Decimal("0.5"),
                Decimal("1.2"),
            ),
            CandleShape(
                pip * Decimal("2.0"),
                pip * Decimal("1.2"),
                pip * Decimal("0.6"),
                Decimal("1.4"),
            ),
        ],
        candle_count,
    )


def generate_crypto_tick_sample(candle_count: int, volatility: Decimal) -> list[CandleShape]:
    tick = max(volatility, Decimal("5.00"))
    return fit_count(
        [
            CandleShape(
                tick * Decimal("0.70"),
                tick * Decimal("0.90"),
                tick * Decimal("0.80"),
                Decimal("1.0"),
            ),
            CandleShape(
                tick * Decimal("-0.40"),
                tick * Decimal("0.70"),
                tick * Decimal("0.90"),
                Decimal("1.1"),
            ),
            CandleShape(
                tick * Decimal("1.40"),
                tick * Decimal("1.60"),
                tick * Decimal("0.80"),
                Decimal("1.6"),
            ),
            CandleShape(
                tick * Decimal("-0.90"),
                tick * Decimal("1.20"),
                tick * Decimal("1.50"),
                Decimal("1.4"),
            ),
        ],
        candle_count,
    )


def directional_shapes(
    candle_count: int,
    volatility: Decimal,
    direction: Decimal,
) -> list[CandleShape]:
    return [
        CandleShape(
            volatility * direction * (Decimal("0.75") + Decimal(index % 3) * Decimal("0.15")),
            volatility * Decimal("0.45"),
            volatility * Decimal("0.45"),
            Decimal("1") + Decimal(index) * Decimal("0.03"),
        )
        for index in range(max(0, candle_count))
    ]


def alternating_range(candle_count: int, amplitude: Decimal) -> list[CandleShape]:
    shapes: list[CandleShape] = []
    for index in range(max(0, candle_count)):
        direction = Decimal("1") if index % 2 == 0 else Decimal("-1")
        shapes.append(
            CandleShape(
                amplitude * direction,
                amplitude * Decimal("1.40"),
                amplitude * Decimal("1.40"),
                Decimal("1"),
            )
        )
    return shapes


def fit_count(shapes: list[CandleShape], candle_count: int) -> list[CandleShape]:
    if not shapes:
        return [
            CandleShape(Decimal("0"), Decimal("0.0001"), Decimal("0.0001"))
            for _ in range(candle_count)
        ]
    if len(shapes) >= candle_count:
        return shapes[:candle_count]
    fitted = list(shapes)
    index = 0
    while len(fitted) < candle_count:
        fitted.append(shapes[index % len(shapes)])
        index += 1
    return fitted
