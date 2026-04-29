from decimal import Decimal

from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    build_candidate,
    common_risk_notes,
    decimal_feature,
    evidence_item,
    latest_lower_wick_ratio,
    latest_upper_wick_ratio,
)


def detect_fakeout(context: PatternDetectionContext) -> PatternCandidateDraft:
    latest_candle = context.analysis_candles[-1]
    previous_candle = context.analysis_candles[-2] if len(context.analysis_candles) >= 2 else None
    previous_range_high = decimal_feature(context.features, "range", "previousRangeHigh")
    previous_range_low = decimal_feature(context.features, "range", "previousRangeLow")
    broke_above = previous_range_high is not None and any(
        candle.high > previous_range_high for candle in context.analysis_candles
    )
    broke_below = previous_range_low is not None and any(
        candle.low < previous_range_low for candle in context.analysis_candles
    )
    closed_inside_range = (
        previous_range_low is not None
        and previous_range_high is not None
        and previous_range_low <= latest_candle.close <= previous_range_high
    )
    upper_wick_ratio = latest_upper_wick_ratio(latest_candle)
    lower_wick_ratio = latest_lower_wick_ratio(latest_candle)
    large_wick = max(upper_wick_ratio, lower_wick_ratio) >= Decimal("0.45")
    reversed_after_break = False
    if previous_candle is not None and broke_above:
        reversed_after_break = latest_candle.close < previous_candle.close
    if previous_candle is not None and broke_below:
        reversed_after_break = reversed_after_break or latest_candle.close > previous_candle.close
    evidence = [
        evidence_item(
            "range_boundary_was_broken",
            broke_above or broke_below,
            {"brokeAbove": broke_above, "brokeBelow": broke_below},
            "break_previous_range",
            Decimal("0.25"),
        ),
        evidence_item(
            "failed_to_hold_outside_range",
            closed_inside_range,
            latest_candle.close,
            "inside_previous_range",
            Decimal("0.25"),
        ),
        evidence_item(
            "large_wick_on_failure",
            large_wick,
            max(upper_wick_ratio, lower_wick_ratio),
            Decimal("0.45"),
            Decimal("0.20"),
        ),
        evidence_item(
            "follow_through_reversed",
            reversed_after_break,
            latest_candle.close,
            "reverse_after_break",
            Decimal("0.20"),
        ),
        evidence_item(
            "baseline_range_available",
            previous_range_high is not None and previous_range_low is not None,
            {"high": previous_range_high, "low": previous_range_low},
            "both_bounds_present",
            Decimal("0.10"),
        ),
    ]
    return build_candidate(
        pattern_type="fakeout",
        bias="neutral",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "previousRangeHigh": previous_range_high,
            "previousRangeLow": previous_range_low,
            "latestClose": latest_candle.close,
            "brokeAbove": broke_above,
            "brokeBelow": broke_below,
            "upperWickRatio": upper_wick_ratio,
            "lowerWickRatio": lower_wick_ratio,
        },
    )
