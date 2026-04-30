from decimal import Decimal
from uuid import uuid4

from app.modules.profile_diagnostics.calculator import (
    DiagnosticThresholds,
    PatternOutcomeDiagnosticResult,
    StrategyProfileDiagnosticResult,
)
from app.modules.profile_diagnostics.models import (
    CalibrationRecommendationStatus,
    CalibrationRecommendationType,
    DiagnosticLabel,
)
from app.modules.profile_diagnostics.recommender import ProfileCalibrationRecommender

WORKSPACE_ID = uuid4()
SYMBOL_ID = uuid4()


def test_recommendation_increase_sample_size() -> None:
    recommendations = recommender().profile_recommendations(
        diagnostic=profile_result(sample_size=2, label=DiagnosticLabel.LOW_SAMPLE),
        profile=None,
        minimum_sample_size=5,
        thresholds=DiagnosticThresholds(),
    )

    assert (
        recommendations[0].recommendation_type == CalibrationRecommendationType.INCREASE_SAMPLE_SIZE
    )


def test_recommendation_review_confidence() -> None:
    recommendations = recommender().profile_recommendations(
        diagnostic=profile_result(
            reversal_rate=Decimal("0.400000"),
            label=DiagnosticLabel.REVERSAL_PRONE,
        ),
        profile=None,
        minimum_sample_size=5,
        thresholds=DiagnosticThresholds(),
    )

    assert any(
        item.recommendation_type == CalibrationRecommendationType.REVIEW_MINIMUM_CONFIDENCE
        for item in recommendations
    )


def test_recommendation_review_candidate_strength() -> None:
    recommendations = recommender().profile_recommendations(
        diagnostic=profile_result(
            no_follow_through_rate=Decimal("0.500000"),
            label=DiagnosticLabel.NEEDS_THRESHOLD_REVIEW,
        ),
        profile=None,
        minimum_sample_size=5,
        thresholds=DiagnosticThresholds(),
    )

    assert any(
        item.recommendation_type == CalibrationRecommendationType.REVIEW_CANDIDATE_STRENGTH
        for item in recommendations
    )


def test_recommendation_no_change() -> None:
    recommendations = recommender().profile_recommendations(
        diagnostic=profile_result(label=DiagnosticLabel.STRONG_FOLLOW_THROUGH),
        profile=None,
        minimum_sample_size=5,
        thresholds=DiagnosticThresholds(),
    )

    assert any(
        item.recommendation_type == CalibrationRecommendationType.NO_CHANGE
        for item in recommendations
    )


def test_pattern_detector_review_recommendation() -> None:
    recommendations = recommender().pattern_recommendations(
        diagnostic=pattern_result(reversal_rate=Decimal("0.500000")),
        thresholds=DiagnosticThresholds(),
    )

    assert (
        recommendations[0].recommendation_type
        == CalibrationRecommendationType.REVIEW_PATTERN_DETECTOR
    )


def test_recommendation_status_validation_enum() -> None:
    assert (
        CalibrationRecommendationStatus("acknowledged")
        == CalibrationRecommendationStatus.ACKNOWLEDGED
    )


def recommender() -> ProfileCalibrationRecommender:
    return ProfileCalibrationRecommender()


def profile_result(
    sample_size: int = 10,
    continuation_rate: Decimal = Decimal("0.700000"),
    reversal_rate: Decimal = Decimal("0.100000"),
    no_follow_through_rate: Decimal = Decimal("0.100000"),
    confidence_alignment_score: Decimal | None = Decimal("0.800000"),
    label: DiagnosticLabel = DiagnosticLabel.STRONG_FOLLOW_THROUGH,
) -> StrategyProfileDiagnosticResult:
    return StrategyProfileDiagnosticResult(
        workspace_id=WORKSPACE_ID,
        horizon_minutes=15,
        sample_size=sample_size,
        evaluated_count=sample_size,
        continuation_count=7,
        partial_follow_through_count=0,
        no_follow_through_count=1,
        reversal_count=1,
        insufficient_data_count=0,
        continuation_rate=continuation_rate,
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_through_rate,
        average_confidence_score=Decimal("0.800000"),
        average_max_favorable_move=None,
        average_max_adverse_move=None,
        average_net_move=None,
        average_max_favorable_pips=None,
        average_max_adverse_pips=None,
        average_net_pips=None,
        average_max_favorable_ticks=None,
        average_max_adverse_ticks=None,
        average_net_ticks=None,
        confidence_alignment_score=confidence_alignment_score,
        diagnostic_label=label,
        diagnostic_summary="summary",
        metadata_json={},
        strategy_profile_key="default",
        strategy_profile_version="v1",
        symbol_id=SYMBOL_ID,
        timeframe="1m",
    )


def pattern_result(
    reversal_rate: Decimal = Decimal("0.100000"),
    no_follow_through_rate: Decimal = Decimal("0.100000"),
) -> PatternOutcomeDiagnosticResult:
    return PatternOutcomeDiagnosticResult(
        workspace_id=WORKSPACE_ID,
        horizon_minutes=15,
        sample_size=10,
        evaluated_count=10,
        continuation_count=4,
        partial_follow_through_count=1,
        no_follow_through_count=1,
        reversal_count=5,
        insufficient_data_count=0,
        continuation_rate=Decimal("0.500000"),
        reversal_rate=reversal_rate,
        no_follow_through_rate=no_follow_through_rate,
        average_confidence_score=Decimal("0.800000"),
        average_max_favorable_move=None,
        average_max_adverse_move=None,
        average_net_move=None,
        average_max_favorable_pips=None,
        average_max_adverse_pips=None,
        average_net_pips=None,
        average_max_favorable_ticks=None,
        average_max_adverse_ticks=None,
        average_net_ticks=None,
        confidence_alignment_score=Decimal("0.800000"),
        diagnostic_label=DiagnosticLabel.REVERSAL_PRONE,
        diagnostic_summary="summary",
        metadata_json={},
        pattern_type="fakeout",
        strategy_profile_key=None,
        symbol_id=None,
        timeframe=None,
    )
