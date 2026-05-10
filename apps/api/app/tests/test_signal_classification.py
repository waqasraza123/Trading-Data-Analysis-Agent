from decimal import Decimal
from typing import cast
from uuid import uuid4

from app.modules.patterns.models import PatternCandidate
from app.modules.signals.confidence import calculate_confidence
from app.modules.signals.conflicts import resolve_conflicts
from app.modules.signals.models import SignalBias, SignalClassificationStatus
from app.modules.signals.service import SignalClassificationService, profile_snapshot
from app.modules.signals.types import CandidateEvaluation
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.strategy_profiles.seeds import DEFAULT_STRATEGY_PROFILES


def test_strategy_profile_defaults_include_required_profiles() -> None:
    profile_keys = {profile.key for profile in DEFAULT_STRATEGY_PROFILES}

    assert profile_keys == {
        "breakout_continuation",
        "reversal_rejection",
        "range_chop_avoidance",
        "fakeout_protection",
    }


def test_strategy_profile_snapshot_stores_replayable_config() -> None:
    profile = profile_from_key("breakout_continuation")

    snapshot = profile_snapshot(profile)

    assert snapshot["key"] == "breakout_continuation"
    assert snapshot["version"] == "v1"
    assert snapshot["minimumCandidateStrength"] == "0.6500"
    allowed_patterns = cast(list[str], snapshot["allowedPatterns"])
    assert "bullish_breakout" in allowed_patterns


def test_candidate_filtering_rejects_patterns_not_allowed_by_profile() -> None:
    service = signal_service()
    profile = profile_from_key("breakout_continuation")
    candidate = pattern_candidate("fakeout", "neutral", "0.9000")

    rejection = service.initial_rejection(profile, candidate)

    assert rejection is not None
    assert rejection.reason_code == "unsupported_pattern_type"


def test_candidate_filtering_rejects_below_minimum_strength() -> None:
    service = signal_service()
    profile = profile_from_key("breakout_continuation")
    candidate = pattern_candidate("bullish_breakout", "bullish", "0.6400")

    rejection = service.initial_rejection(profile, candidate)

    assert rejection is not None
    assert rejection.reason_code == "below_minimum_strength"


def test_confidence_weighted_scoring() -> None:
    profile = profile_from_key("breakout_continuation")
    candidate = pattern_candidate("bullish_breakout", "bullish", "0.8000")

    result = calculate_confidence(
        candidate=candidate,
        component_weights=profile.component_weights_json,
        features=strong_bullish_features(),
        indicators=strong_bullish_indicators(),
    )

    assert result.confidence_score >= Decimal("0.8000")
    assert {component.component_name for component in result.components} == {
        "pattern_strength",
        "trend_alignment",
        "volatility_confirmation",
        "indicator_support",
        "data_quality",
    }


def test_missing_snapshots_degrade_confidence_without_crashing() -> None:
    profile = profile_from_key("breakout_continuation")
    candidate = pattern_candidate("bullish_breakout", "bullish", "0.8000")

    result = calculate_confidence(
        candidate=candidate,
        component_weights=profile.component_weights_json,
        features=None,
        indicators=None,
    )

    assert result.confidence_score < Decimal("0.7000")
    assert {note["code"] for note in result.risk_notes} == {
        "missing_feature_snapshot",
        "missing_indicator_snapshot",
    }


def test_candidate_filtering_rejects_below_minimum_confidence() -> None:
    service = signal_service()
    profile = profile_from_key("breakout_continuation")
    candidate = pattern_candidate("bullish_breakout", "bullish", "0.8000")
    confidence = calculate_confidence(
        candidate=candidate,
        component_weights=profile.component_weights_json,
        features=weak_bullish_features(),
        indicators=weak_bullish_indicators(),
    )

    rejection = service.metric_rejection(profile, candidate, confidence, weak_bullish_features())

    assert rejection is not None
    assert rejection.reason_code == "below_minimum_confidence"


def test_low_data_quality_rejects_candidate() -> None:
    service = signal_service()
    profile = profile_from_key("breakout_continuation")
    candidate = pattern_candidate("bullish_breakout", "bullish", "0.8000")
    features = strong_bullish_features(data_quality="0.5000")
    confidence = calculate_confidence(
        candidate=candidate,
        component_weights=profile.component_weights_json,
        features=features,
        indicators=strong_bullish_indicators(),
    )

    rejection = service.metric_rejection(profile, candidate, confidence, features)

    assert rejection is not None
    assert rejection.reason_code == "low_data_quality"


def test_fakeout_overrides_breakout_within_margin() -> None:
    breakout = evaluation(
        profile_from_key("breakout_continuation"),
        pattern_candidate("bullish_breakout", "bullish", "0.7000"),
        "0.7000",
    )
    fakeout = evaluation(
        profile_from_key("fakeout_protection"),
        pattern_candidate("fakeout", "neutral", "0.6200"),
        "0.6200",
    )

    decision = resolve_conflicts([breakout, fakeout])

    assert decision.classification_status == SignalClassificationStatus.NO_SIGNAL
    assert decision.bias == SignalBias.NEUTRAL
    assert decision.no_signal_reason == "fakeout_risk"
    assert decision.selected_evaluation is fakeout


def test_chop_candidate_blocks_directional_signal() -> None:
    breakout = evaluation(
        profile_from_key("breakout_continuation"),
        pattern_candidate("bullish_breakout", "bullish", "0.6900"),
        "0.7000",
    )
    chop = evaluation(
        profile_from_key("range_chop_avoidance"),
        pattern_candidate("sideways_range", "neutral", "0.6400"),
        "0.7000",
    )

    decision = resolve_conflicts([breakout, chop])

    assert decision.classification_status == SignalClassificationStatus.NO_SIGNAL
    assert decision.no_signal_reason == "chop_or_sideways_market"


def test_conflicting_directional_candidates_create_unclear_no_signal() -> None:
    bullish = evaluation(
        profile_from_key("breakout_continuation"),
        pattern_candidate("bullish_breakout", "bullish", "0.7200"),
        "0.7200",
    )
    bearish = evaluation(
        profile_from_key("breakout_continuation"),
        pattern_candidate("bearish_breakdown", "bearish", "0.7000"),
        "0.7100",
    )

    decision = resolve_conflicts([bullish, bearish])

    assert decision.classification_status == SignalClassificationStatus.UNCLEAR
    assert decision.bias == SignalBias.UNCLEAR
    assert decision.no_signal_reason == "conflicting_directional_candidates"


def test_reversal_beats_continuation_only_when_margin_allows() -> None:
    continuation = evaluation(
        profile_from_key("breakout_continuation"),
        pattern_candidate("bullish_continuation", "bullish", "0.7100"),
        "0.7100",
    )
    reversal = evaluation(
        profile_from_key("reversal_rejection"),
        pattern_candidate("bullish_reversal", "bullish", "0.7400"),
        "0.7400",
    )

    decision = resolve_conflicts([reversal, continuation])

    assert decision.selected_evaluation is continuation


def test_missing_pattern_candidates_would_create_no_signal_reason() -> None:
    decision = resolve_conflicts([])

    assert decision.classification_status == SignalClassificationStatus.NO_SIGNAL
    assert decision.no_signal_reason == "no_profile_candidates"


def test_golden_bullish_breakout_classification() -> None:
    decision = resolve_conflicts(
        [
            evaluation(
                profile_from_key("breakout_continuation"),
                pattern_candidate("bullish_breakout", "bullish", "0.7800"),
                "0.7600",
            )
        ]
    )

    assert decision.classification_status == SignalClassificationStatus.SIGNAL
    assert decision.bias == SignalBias.BULLISH


def test_golden_bearish_breakdown_classification() -> None:
    decision = resolve_conflicts(
        [
            evaluation(
                profile_from_key("breakout_continuation"),
                pattern_candidate("bearish_breakdown", "bearish", "0.7800"),
                "0.7600",
            )
        ]
    )

    assert decision.classification_status == SignalClassificationStatus.SIGNAL
    assert decision.bias == SignalBias.BEARISH


def test_golden_fakeout_protection_no_signal() -> None:
    test_fakeout_overrides_breakout_within_margin()


def test_golden_range_chop_avoidance_no_signal() -> None:
    test_chop_candidate_blocks_directional_signal()


def test_golden_reversal_rejection_classification() -> None:
    decision = resolve_conflicts(
        [
            evaluation(
                profile_from_key("reversal_rejection"),
                pattern_candidate("bullish_reversal", "bullish", "0.8000"),
                "0.7900",
            )
        ]
    )

    assert decision.classification_status == SignalClassificationStatus.SIGNAL
    assert decision.bias == SignalBias.BULLISH


def test_golden_conflicting_candidates_unclear() -> None:
    test_conflicting_directional_candidates_create_unclear_no_signal()


def signal_service() -> SignalClassificationService:
    return SignalClassificationService.__new__(SignalClassificationService)


def profile_from_key(key: str) -> StrategyProfile:
    definition = next(profile for profile in DEFAULT_STRATEGY_PROFILES if profile.key == key)
    return StrategyProfile(
        id=uuid4(),
        key=definition.key,
        name=definition.name,
        description=definition.description,
        version=definition.version,
        is_active=True,
        allowed_patterns_json=list(definition.allowed_patterns),
        excluded_patterns_json=list(definition.excluded_patterns),
        minimum_candidate_strength=definition.minimum_candidate_strength,
        minimum_confidence=definition.minimum_confidence,
        component_weights_json=definition.component_weights,
        risk_filters_json=definition.risk_filters,
        no_signal_rules_json=definition.no_signal_rules,
    )


def pattern_candidate(pattern_type: str, bias: str, strength_score: str) -> PatternCandidate:
    return PatternCandidate(
        id=uuid4(),
        analysis_run_id=uuid4(),
        workspace_id=uuid4(),
        symbol_id=uuid4(),
        pattern_type=pattern_type,
        bias=bias,
        strength_score=Decimal(strength_score),
        is_selected=False,
        evidence_json=[
            {
                "name": "test_evidence",
                "passed": True,
                "value": strength_score,
                "threshold": "0.5000",
                "weight": "1.0000",
            }
        ],
        risk_notes_json=[],
        metrics_json={},
    )


def evaluation(
    profile: StrategyProfile,
    candidate: PatternCandidate,
    ranking_score: str,
) -> CandidateEvaluation:
    features = (
        strong_bullish_features() if candidate.bias != "bearish" else strong_bearish_features()
    )
    indicators = (
        strong_bullish_indicators() if candidate.bias != "bearish" else strong_bearish_indicators()
    )
    confidence = calculate_confidence(
        candidate=candidate,
        component_weights=profile.component_weights_json,
        features=features,
        indicators=indicators,
    )
    return CandidateEvaluation(
        profile=profile,
        candidate=candidate,
        confidence=confidence,
        ranking_score=Decimal(ranking_score),
        classifier_evidence=(),
        risk_notes=(),
    )


def strong_bullish_features(data_quality: str = "1.0000") -> dict[str, object]:
    return {
        "trend": {"trendState": "short_term_uptrend"},
        "volatility": {"volatilityState": "expanding"},
        "dataQuality": {"qualityScore": data_quality},
        "movement": {"movementEfficiency": "0.7000", "netDirection": "bullish"},
        "range": {"rangeState": "above_previous_range"},
    }


def strong_bearish_features(data_quality: str = "1.0000") -> dict[str, object]:
    return {
        "trend": {"trendState": "short_term_downtrend"},
        "volatility": {"volatilityState": "expanding"},
        "dataQuality": {"qualityScore": data_quality},
        "movement": {"movementEfficiency": "0.7000", "netDirection": "bearish"},
        "range": {"rangeState": "below_previous_range"},
    }


def weak_bullish_features() -> dict[str, object]:
    return {
        "trend": {"trendState": "mixed_or_sideways"},
        "volatility": {"volatilityState": "compressed"},
        "dataQuality": {"qualityScore": "1.0000"},
        "movement": {"movementEfficiency": "0.1000", "netDirection": "neutral"},
        "range": {"rangeState": "inside_previous_range"},
    }


def strong_bullish_indicators() -> dict[str, object]:
    return {
        "ema": {"alignment": "bullish_alignment"},
        "rsi": {"state": "bullish_momentum"},
        "macd": {"state": "bullish"},
    }


def strong_bearish_indicators() -> dict[str, object]:
    return {
        "ema": {"alignment": "bearish_alignment"},
        "rsi": {"state": "bearish_momentum"},
        "macd": {"state": "bearish"},
    }


def weak_bullish_indicators() -> dict[str, object]:
    return {
        "ema": {"alignment": "bearish_alignment"},
        "rsi": {"state": "bearish_momentum"},
        "macd": {"state": "bearish"},
    }
