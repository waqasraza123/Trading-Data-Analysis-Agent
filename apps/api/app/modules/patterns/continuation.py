from decimal import Decimal

from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    build_candidate,
    common_risk_notes,
    decimal_feature,
    evidence_item,
    integer_feature,
    mapping_feature,
    recent_price_resumed_down,
    recent_price_resumed_up,
    string_feature,
)


def detect_bullish_continuation(context: PatternDetectionContext) -> PatternCandidateDraft:
    trend_state = string_feature(context.features, "trend", "trendState")
    ema_alignment = mapping_feature(context.indicators, "ema").get("alignment")
    movement_efficiency = decimal_feature(context.features, "movement", "movementEfficiency")
    higher_lows_count = integer_feature(context.features, "trend", "higherLowsCount")
    lower_lows_count = integer_feature(context.features, "trend", "lowerLowsCount")
    pullback_preserved = higher_lows_count >= lower_lows_count
    evidence = [
        evidence_item(
            "short_term_uptrend",
            trend_state == "short_term_uptrend",
            trend_state,
            "short_term_uptrend",
            Decimal("0.25"),
        ),
        evidence_item(
            "bullish_ema_alignment",
            ema_alignment == "bullish_alignment",
            ema_alignment,
            "bullish_alignment",
            Decimal("0.20"),
        ),
        evidence_item(
            "pullback_preserved_higher_low_structure",
            pullback_preserved,
            higher_lows_count - lower_lows_count,
            "non_negative",
            Decimal("0.20"),
        ),
        evidence_item(
            "price_resumed_upward",
            recent_price_resumed_up(context.analysis_candles),
            context.analysis_candles[-1].close,
            "close_above_previous_close_and_open",
            Decimal("0.20"),
        ),
        evidence_item(
            "movement_efficiency_not_choppy",
            movement_efficiency is not None and movement_efficiency >= Decimal("0.30"),
            movement_efficiency,
            Decimal("0.30"),
            Decimal("0.15"),
        ),
    ]
    return build_candidate(
        pattern_type="bullish_continuation",
        bias="bullish",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "trendState": trend_state,
            "emaAlignment": ema_alignment,
            "higherLowsCount": higher_lows_count,
            "lowerLowsCount": lower_lows_count,
            "movementEfficiency": movement_efficiency,
        },
    )


def detect_bearish_continuation(context: PatternDetectionContext) -> PatternCandidateDraft:
    trend_state = string_feature(context.features, "trend", "trendState")
    ema_alignment = mapping_feature(context.indicators, "ema").get("alignment")
    movement_efficiency = decimal_feature(context.features, "movement", "movementEfficiency")
    lower_highs_count = integer_feature(context.features, "trend", "lowerHighsCount")
    higher_highs_count = integer_feature(context.features, "trend", "higherHighsCount")
    pullback_preserved = lower_highs_count >= higher_highs_count
    evidence = [
        evidence_item(
            "short_term_downtrend",
            trend_state == "short_term_downtrend",
            trend_state,
            "short_term_downtrend",
            Decimal("0.25"),
        ),
        evidence_item(
            "bearish_ema_alignment",
            ema_alignment == "bearish_alignment",
            ema_alignment,
            "bearish_alignment",
            Decimal("0.20"),
        ),
        evidence_item(
            "pullback_preserved_lower_high_structure",
            pullback_preserved,
            lower_highs_count - higher_highs_count,
            "non_negative",
            Decimal("0.20"),
        ),
        evidence_item(
            "price_resumed_downward",
            recent_price_resumed_down(context.analysis_candles),
            context.analysis_candles[-1].close,
            "close_below_previous_close_and_open",
            Decimal("0.20"),
        ),
        evidence_item(
            "movement_efficiency_not_choppy",
            movement_efficiency is not None and movement_efficiency >= Decimal("0.30"),
            movement_efficiency,
            Decimal("0.30"),
            Decimal("0.15"),
        ),
    ]
    return build_candidate(
        pattern_type="bearish_continuation",
        bias="bearish",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "trendState": trend_state,
            "emaAlignment": ema_alignment,
            "lowerHighsCount": lower_highs_count,
            "higherHighsCount": higher_highs_count,
            "movementEfficiency": movement_efficiency,
        },
    )
