from decimal import Decimal

from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    build_candidate,
    common_risk_notes,
    consecutive_closes_above,
    decimal_feature,
    evidence_item,
    integer_feature,
    latest_body_ratio,
    string_feature,
)


def detect_bullish_breakout(context: PatternDetectionContext) -> PatternCandidateDraft:
    latest_candle = context.analysis_candles[-1]
    previous_range_high = decimal_feature(context.features, "range", "previousRangeHigh")
    hold_count = consecutive_closes_above(context.analysis_candles, previous_range_high)
    volatility_state = string_feature(context.features, "volatility", "volatilityState")
    higher_lows_count = integer_feature(context.features, "trend", "higherLowsCount")
    lower_lows_count = integer_feature(context.features, "trend", "lowerLowsCount")
    body_ratio = latest_body_ratio(latest_candle)
    evidence = [
        evidence_item(
            "close_above_previous_range_high",
            previous_range_high is not None and latest_candle.close > previous_range_high,
            latest_candle.close,
            previous_range_high,
            Decimal("0.25"),
        ),
        evidence_item(
            "hold_above_range_high",
            hold_count >= 2,
            hold_count,
            2,
            Decimal("0.20"),
        ),
        evidence_item(
            "volatility_supports_breakout",
            volatility_state in {"normal", "expanding"},
            volatility_state,
            "normal_or_expanding",
            Decimal("0.15"),
        ),
        evidence_item(
            "higher_lows_structure",
            higher_lows_count > lower_lows_count,
            higher_lows_count - lower_lows_count,
            "positive",
            Decimal("0.20"),
        ),
        evidence_item(
            "breakout_body_strength",
            latest_candle.close > latest_candle.open and body_ratio >= Decimal("0.45"),
            body_ratio,
            Decimal("0.45"),
            Decimal("0.20"),
        ),
    ]
    return build_candidate(
        pattern_type="bullish_breakout",
        bias="bullish",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "previousRangeHigh": previous_range_high,
            "latestClose": latest_candle.close,
            "holdCount": hold_count,
            "higherLowsCount": higher_lows_count,
            "lowerLowsCount": lower_lows_count,
            "bodyToRangeRatio": body_ratio,
        },
    )
