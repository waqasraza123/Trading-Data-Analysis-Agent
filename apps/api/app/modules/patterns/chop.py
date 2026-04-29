from decimal import Decimal

from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    build_candidate,
    close_direction_changes,
    common_risk_notes,
    decimal_feature,
    evidence_item,
    string_feature,
)


def detect_sideways_range(context: PatternDetectionContext) -> PatternCandidateDraft:
    range_state = string_feature(context.features, "range", "rangeState")
    trend_state = string_feature(context.features, "trend", "trendState")
    volatility_state = string_feature(context.features, "volatility", "volatilityState")
    movement_efficiency = decimal_feature(context.features, "movement", "movementEfficiency")
    direction_changes = close_direction_changes(context.analysis_candles)
    evidence = [
        evidence_item(
            "price_inside_previous_range",
            range_state == "inside_previous_range",
            range_state,
            "inside_previous_range",
            Decimal("0.25"),
        ),
        evidence_item(
            "low_net_movement",
            movement_efficiency is not None and movement_efficiency <= Decimal("0.35"),
            movement_efficiency,
            Decimal("0.35"),
            Decimal("0.20"),
        ),
        evidence_item(
            "mixed_high_low_structure",
            trend_state == "mixed_or_sideways",
            trend_state,
            "mixed_or_sideways",
            Decimal("0.20"),
        ),
        evidence_item(
            "atr_not_expanding",
            volatility_state in {"compressed", "normal"},
            volatility_state,
            "compressed_or_normal",
            Decimal("0.15"),
        ),
        evidence_item(
            "frequent_direction_changes",
            direction_changes >= max(2, len(context.analysis_candles) // 3),
            direction_changes,
            max(2, len(context.analysis_candles) // 3),
            Decimal("0.20"),
        ),
    ]
    return build_candidate(
        pattern_type="sideways_range",
        bias="neutral",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "rangeState": range_state,
            "trendState": trend_state,
            "volatilityState": volatility_state,
            "movementEfficiency": movement_efficiency,
            "directionChanges": direction_changes,
        },
    )


def detect_low_volatility_chop(context: PatternDetectionContext) -> PatternCandidateDraft:
    range_state = string_feature(context.features, "range", "rangeState")
    volatility_state = string_feature(context.features, "volatility", "volatilityState")
    body_to_range_ratio = decimal_feature(context.features, "candleShape", "bodyToRangeRatio")
    movement_efficiency = decimal_feature(context.features, "movement", "movementEfficiency")
    direction_changes = close_direction_changes(context.analysis_candles)
    evidence = [
        evidence_item(
            "small_average_bodies",
            body_to_range_ratio is not None and body_to_range_ratio <= Decimal("0.35"),
            body_to_range_ratio,
            Decimal("0.35"),
            Decimal("0.25"),
        ),
        evidence_item(
            "compressed_atr",
            volatility_state == "compressed",
            volatility_state,
            "compressed",
            Decimal("0.20"),
        ),
        evidence_item(
            "low_movement_efficiency",
            movement_efficiency is not None and movement_efficiency <= Decimal("0.25"),
            movement_efficiency,
            Decimal("0.25"),
            Decimal("0.20"),
        ),
        evidence_item(
            "many_direction_changes",
            direction_changes >= max(2, len(context.analysis_candles) // 3),
            direction_changes,
            max(2, len(context.analysis_candles) // 3),
            Decimal("0.20"),
        ),
        evidence_item(
            "no_clean_breakout",
            range_state in {"inside_previous_range", "no_baseline_range"},
            range_state,
            "inside_previous_range_or_no_baseline_range",
            Decimal("0.15"),
        ),
    ]
    return build_candidate(
        pattern_type="low_volatility_chop",
        bias="neutral",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "rangeState": range_state,
            "volatilityState": volatility_state,
            "bodyToRangeRatio": body_to_range_ratio,
            "movementEfficiency": movement_efficiency,
            "directionChanges": direction_changes,
        },
    )
