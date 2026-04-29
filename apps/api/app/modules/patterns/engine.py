from collections.abc import Mapping
from typing import Any

from app.modules.candles.models import Candle
from app.modules.patterns.bearish_breakdown import detect_bearish_breakdown
from app.modules.patterns.bullish_breakout import detect_bullish_breakout
from app.modules.patterns.chop import detect_low_volatility_chop, detect_sideways_range
from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    selected_candidates,
)
from app.modules.patterns.continuation import (
    detect_bearish_continuation,
    detect_bullish_continuation,
)
from app.modules.patterns.fakeout import detect_fakeout
from app.modules.patterns.reversal import detect_bearish_reversal, detect_bullish_reversal


def detect_pattern_candidates(
    analysis_candles: list[Candle],
    baseline_candles: list[Candle],
    features: Mapping[str, Any],
    indicators: Mapping[str, Any],
) -> list[PatternCandidateDraft]:
    if not analysis_candles:
        return []
    context = PatternDetectionContext(
        analysis_candles=analysis_candles,
        baseline_candles=baseline_candles,
        features=features,
        indicators=indicators,
    )
    candidates = [
        detect_bullish_breakout(context),
        detect_bearish_breakdown(context),
        detect_bullish_continuation(context),
        detect_bearish_continuation(context),
        detect_bullish_reversal(context),
        detect_bearish_reversal(context),
        detect_fakeout(context),
        detect_sideways_range(context),
        detect_low_volatility_chop(context),
    ]
    return selected_candidates(candidates)
