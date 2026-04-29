from typing import Any

from app.modules.candles.models import Candle
from app.modules.candles.quality import CandleQualityReport
from app.modules.features.candle_shape import calculate_candle_shape_features
from app.modules.features.movement import calculate_movement_features
from app.modules.features.range import calculate_range_features
from app.modules.features.serialization import serialize_feature_map
from app.modules.features.trend import calculate_trend_features
from app.modules.features.volatility import calculate_volatility_features
from app.modules.symbols.models import Symbol


def calculate_feature_snapshot(
    symbol: Symbol,
    analysis_candles: list[Candle],
    warmup_candles: list[Candle],
    baseline_candles: list[Candle],
    data_quality: CandleQualityReport,
) -> dict[str, object]:
    features: dict[str, Any] = {
        "movement": calculate_movement_features(analysis_candles, symbol),
        "candleShape": calculate_candle_shape_features(analysis_candles),
        "range": calculate_range_features(analysis_candles, baseline_candles),
        "volatility": calculate_volatility_features(
            analysis_candles,
            warmup_candles,
            baseline_candles,
        ),
        "trend": calculate_trend_features(analysis_candles),
        "dataQuality": data_quality.model_dump(mode="json"),
    }
    return serialize_feature_map(features)
