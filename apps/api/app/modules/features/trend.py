from decimal import Decimal

from app.modules.candles.models import Candle


def calculate_trend_features(candles: list[Candle]) -> dict[str, object]:
    higher_highs_count = count_higher_values([candle.high for candle in candles])
    higher_lows_count = count_higher_values([candle.low for candle in candles])
    lower_highs_count = count_lower_values([candle.high for candle in candles])
    lower_lows_count = count_lower_values([candle.low for candle in candles])
    trend_slope = candles[-1].close - candles[0].open
    return {
        "higherHighsCount": higher_highs_count,
        "higherLowsCount": higher_lows_count,
        "lowerHighsCount": lower_highs_count,
        "lowerLowsCount": lower_lows_count,
        "trendSlope": trend_slope,
        "trendState": trend_state(
            trend_slope,
            higher_highs_count,
            higher_lows_count,
            lower_highs_count,
            lower_lows_count,
        ),
    }


def count_higher_values(values: list[Decimal]) -> int:
    return sum(
        1 for previous, current in zip(values, values[1:], strict=False) if current > previous
    )


def count_lower_values(values: list[Decimal]) -> int:
    return sum(
        1 for previous, current in zip(values, values[1:], strict=False) if current < previous
    )


def trend_state(
    trend_slope: Decimal,
    higher_highs_count: int,
    higher_lows_count: int,
    lower_highs_count: int,
    lower_lows_count: int,
) -> str:
    bullish_structure = higher_highs_count + higher_lows_count
    bearish_structure = lower_highs_count + lower_lows_count
    if trend_slope > 0 and bullish_structure > bearish_structure:
        return "short_term_uptrend"
    if trend_slope < 0 and bearish_structure > bullish_structure:
        return "short_term_downtrend"
    return "mixed_or_sideways"
