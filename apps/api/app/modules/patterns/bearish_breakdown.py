from decimal import Decimal

from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    build_candidate,
    common_risk_notes,
    consecutive_closes_below,
    decimal_feature,
    evidence_item,
    integer_feature,
    latest_body_ratio,
    string_feature,
)


def detect_bearish_breakdown(context: PatternDetectionContext) -> PatternCandidateDraft:
    latest_candle = context.analysis_candles[-1]
    previous_range_low = decimal_feature(context.features, "range", "previousRangeLow")
    hold_count = consecutive_closes_below(context.analysis_candles, previous_range_low)
    volatility_state = string_feature(context.features, "volatility", "volatilityState")
    lower_highs_count = integer_feature(context.features, "trend", "lowerHighsCount")
    higher_highs_count = integer_feature(context.features, "trend", "higherHighsCount")
    body_ratio = latest_body_ratio(latest_candle)
    evidence = [
        evidence_item(
            "close_below_previous_range_low",
            previous_range_low is not None and latest_candle.close < previous_range_low,
            latest_candle.close,
            previous_range_low,
            Decimal("0.25"),
        ),
        evidence_item(
            "hold_below_range_low",
            hold_count >= 2,
            hold_count,
            2,
            Decimal("0.20"),
        ),
        evidence_item(
            "volatility_supports_breakdown",
            volatility_state in {"normal", "expanding"},
            volatility_state,
            "normal_or_expanding",
            Decimal("0.15"),
        ),
        evidence_item(
            "lower_highs_structure",
            lower_highs_count > higher_highs_count,
            lower_highs_count - higher_highs_count,
            "positive",
            Decimal("0.20"),
        ),
        evidence_item(
            "breakdown_body_strength",
            latest_candle.close < latest_candle.open and body_ratio >= Decimal("0.45"),
            body_ratio,
            Decimal("0.45"),
            Decimal("0.20"),
        ),
    ]
    return build_candidate(
        pattern_type="bearish_breakdown",
        bias="bearish",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "previousRangeLow": previous_range_low,
            "latestClose": latest_candle.close,
            "holdCount": hold_count,
            "lowerHighsCount": lower_highs_count,
            "higherHighsCount": higher_highs_count,
            "bodyToRangeRatio": body_ratio,
        },
    )
