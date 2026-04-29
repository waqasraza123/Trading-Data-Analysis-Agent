from decimal import Decimal

from app.modules.candles.models import Candle
from app.modules.indicators.atr import atr_state, calculate_atr
from app.modules.indicators.ema import ema_alignment, latest_ema
from app.modules.indicators.macd import calculate_macd
from app.modules.indicators.rsi import calculate_rsi, rsi_state
from app.modules.indicators.serialization import serialize_indicator_map


def calculate_indicator_snapshot(
    analysis_candles: list[Candle],
    warmup_candles: list[Candle],
    baseline_candles: list[Candle],
) -> dict[str, object]:
    indicator_candles = warmup_candles + analysis_candles
    close_values = [candle.close for candle in indicator_candles]
    ema9 = latest_ema(close_values, 9)
    ema21 = latest_ema(close_values, 21)
    ema50 = latest_ema(close_values, 50)
    rsi14 = calculate_rsi(close_values, 14)
    atr14 = calculate_atr(indicator_candles, 14)
    baseline_atr14 = calculate_atr(baseline_candles, 14)
    indicators = {
        "ema": {
            "ema9": ema9,
            "ema21": ema21,
            "ema50": ema50,
            "alignment": ema_alignment(ema9, ema21, ema50),
            "isReady": ema9 is not None and ema21 is not None and ema50 is not None,
        },
        "rsi": {
            "period": 14,
            "value": rsi14,
            "state": rsi_state(rsi14),
            "isReady": rsi14 is not None,
        },
        "macd": calculate_macd(close_values),
        "atr": {
            "period": 14,
            "value": atr14,
            "baselineValue": baseline_atr14,
            "state": atr_state(atr14, baseline_atr14),
            "isReady": atr14 is not None,
        },
        "calculation": {
            "analysisCandleCount": len(analysis_candles),
            "warmupCandleCount": len(warmup_candles),
            "baselineCandleCount": len(baseline_candles),
            "inputCandleCount": len(indicator_candles),
            "isReady": indicator_set_is_ready(ema9, ema21, ema50, rsi14, atr14),
        },
    }
    return serialize_indicator_map(indicators)


def indicator_set_is_ready(
    ema9: Decimal | None,
    ema21: Decimal | None,
    ema50: Decimal | None,
    rsi14: Decimal | None,
    atr14: Decimal | None,
) -> bool:
    return all(value is not None for value in [ema9, ema21, ema50, rsi14, atr14])
