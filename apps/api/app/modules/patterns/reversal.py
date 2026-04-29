from decimal import Decimal

from app.modules.patterns.common import (
    PatternCandidateDraft,
    PatternDetectionContext,
    as_decimal,
    build_candidate,
    common_risk_notes,
    decimal_feature,
    evidence_item,
    first_half_direction,
    latest_lower_wick_ratio,
    latest_upper_wick_ratio,
    mapping_feature,
    recent_price_resumed_down,
    recent_price_resumed_up,
)


def detect_bullish_reversal(context: PatternDetectionContext) -> PatternCandidateDraft:
    latest_candle = context.analysis_candles[-1]
    previous_range_low = decimal_feature(context.features, "range", "previousRangeLow")
    lower_wick_ratio = latest_lower_wick_ratio(latest_candle)
    rsi_value = as_decimal(mapping_feature(context.indicators, "rsi").get("value"))
    previous_direction = first_half_direction(context.analysis_candles)
    support_rejected = (
        previous_range_low is not None
        and latest_candle.low <= previous_range_low
        and latest_candle.close > previous_range_low
    )
    evidence = [
        evidence_item(
            "previous_bearish_movement",
            previous_direction == "bearish",
            previous_direction,
            "bearish",
            Decimal("0.20"),
        ),
        evidence_item(
            "support_rejection",
            support_rejected,
            latest_candle.low,
            previous_range_low,
            Decimal("0.25"),
        ),
        evidence_item(
            "large_lower_wick",
            lower_wick_ratio >= Decimal("0.45"),
            lower_wick_ratio,
            Decimal("0.45"),
            Decimal("0.20"),
        ),
        evidence_item(
            "follow_through_higher_close",
            recent_price_resumed_up(context.analysis_candles),
            latest_candle.close,
            "close_above_previous_close_and_open",
            Decimal("0.20"),
        ),
        evidence_item(
            "rsi_recovered",
            rsi_value is not None and rsi_value >= Decimal("45"),
            rsi_value,
            Decimal("45"),
            Decimal("0.15"),
        ),
    ]
    return build_candidate(
        pattern_type="bullish_reversal",
        bias="bullish",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "previousDirection": previous_direction,
            "previousRangeLow": previous_range_low,
            "latestLow": latest_candle.low,
            "latestClose": latest_candle.close,
            "lowerWickRatio": lower_wick_ratio,
            "rsi14": rsi_value,
        },
    )


def detect_bearish_reversal(context: PatternDetectionContext) -> PatternCandidateDraft:
    latest_candle = context.analysis_candles[-1]
    previous_range_high = decimal_feature(context.features, "range", "previousRangeHigh")
    upper_wick_ratio = latest_upper_wick_ratio(latest_candle)
    rsi_value = as_decimal(mapping_feature(context.indicators, "rsi").get("value"))
    previous_direction = first_half_direction(context.analysis_candles)
    resistance_rejected = (
        previous_range_high is not None
        and latest_candle.high >= previous_range_high
        and latest_candle.close < previous_range_high
    )
    evidence = [
        evidence_item(
            "previous_bullish_movement",
            previous_direction == "bullish",
            previous_direction,
            "bullish",
            Decimal("0.20"),
        ),
        evidence_item(
            "resistance_rejection",
            resistance_rejected,
            latest_candle.high,
            previous_range_high,
            Decimal("0.25"),
        ),
        evidence_item(
            "large_upper_wick",
            upper_wick_ratio >= Decimal("0.45"),
            upper_wick_ratio,
            Decimal("0.45"),
            Decimal("0.20"),
        ),
        evidence_item(
            "follow_through_lower_close",
            recent_price_resumed_down(context.analysis_candles),
            latest_candle.close,
            "close_below_previous_close_and_open",
            Decimal("0.20"),
        ),
        evidence_item(
            "rsi_weakened",
            rsi_value is not None and rsi_value <= Decimal("55"),
            rsi_value,
            Decimal("55"),
            Decimal("0.15"),
        ),
    ]
    return build_candidate(
        pattern_type="bearish_reversal",
        bias="bearish",
        evidence=evidence,
        risk_notes=common_risk_notes(context),
        metrics={
            "previousDirection": previous_direction,
            "previousRangeHigh": previous_range_high,
            "latestHigh": latest_candle.high,
            "latestClose": latest_candle.close,
            "upperWickRatio": upper_wick_ratio,
            "rsi14": rsi_value,
        },
    )
