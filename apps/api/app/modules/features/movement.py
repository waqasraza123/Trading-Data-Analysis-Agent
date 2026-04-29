from decimal import Decimal

from app.modules.candles.models import Candle
from app.modules.symbols.models import Symbol


def calculate_movement_features(candles: list[Candle], symbol: Symbol) -> dict[str, object]:
    first_candle = candles[0]
    last_candle = candles[-1]
    start_price = first_candle.open
    end_price = last_candle.close
    absolute_move = end_price - start_price
    total_candle_movement = sum((candle.high - candle.low for candle in candles), Decimal("0"))
    return {
        "startPrice": start_price,
        "endPrice": end_price,
        "absoluteMove": absolute_move,
        "percentageMove": safe_ratio(absolute_move, start_price) * Decimal("100"),
        "pipsMoved": calculate_pips_moved(absolute_move, symbol),
        "ticksMoved": calculate_ticks_moved(absolute_move, symbol),
        "netDirection": direction_from_move(absolute_move),
        "totalCandleMovement": total_candle_movement,
        "movementEfficiency": safe_ratio(abs(absolute_move), total_candle_movement),
    }


def calculate_pips_moved(absolute_move: Decimal, symbol: Symbol) -> Decimal | None:
    if symbol.pip_size is None:
        return None
    return absolute_move / symbol.pip_size


def calculate_ticks_moved(absolute_move: Decimal, symbol: Symbol) -> Decimal | None:
    if symbol.tick_size is None:
        return None
    return absolute_move / symbol.tick_size


def direction_from_move(value: Decimal) -> str:
    if value > 0:
        return "bullish"
    if value < 0:
        return "bearish"
    return "neutral"


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator
