from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.profile_diagnostics.calculator import (
    DiagnosticOutcome,
    DiagnosticThresholds,
    ProfileDiagnosticCalculator,
    StrategyProfileDiagnosticResult,
    confidence_alignment_score,
)
from app.modules.profile_diagnostics.models import DiagnosticLabel
from app.modules.signals.models import SignalBias, SignalClassificationStatus

WORKSPACE_ID = uuid4()
SYMBOL_ID = uuid4()


def test_low_sample_diagnostic_label() -> None:
    diagnostic = profile_diagnostic([outcome(OutcomeLabel.CONTINUATION)], minimum_sample_size=2)

    assert diagnostic.diagnostic_label == DiagnosticLabel.LOW_SAMPLE


def test_strong_follow_through_diagnostic_label() -> None:
    diagnostic = profile_diagnostic(
        [
            *[outcome(OutcomeLabel.CONTINUATION) for _ in range(7)],
            *[outcome(OutcomeLabel.PARTIAL_FOLLOW_THROUGH) for _ in range(2)],
            outcome(OutcomeLabel.NO_FOLLOW_THROUGH, confidence_score="0.3000"),
        ],
        minimum_sample_size=5,
    )

    assert diagnostic.diagnostic_label == DiagnosticLabel.STRONG_FOLLOW_THROUGH
    assert diagnostic.continuation_rate == Decimal("0.900000")


def test_reversal_prone_diagnostic_label() -> None:
    diagnostic = profile_diagnostic(
        [
            *[outcome(OutcomeLabel.REVERSAL, confidence_score="0.3000") for _ in range(4)],
            *[outcome(OutcomeLabel.CONTINUATION, confidence_score="0.9000") for _ in range(6)],
        ],
        minimum_sample_size=5,
    )

    assert diagnostic.diagnostic_label == DiagnosticLabel.REVERSAL_PRONE
    assert diagnostic.reversal_rate == Decimal("0.400000")


def test_high_no_follow_through_diagnostic_label() -> None:
    diagnostic = profile_diagnostic(
        [
            *[outcome(OutcomeLabel.NO_FOLLOW_THROUGH, confidence_score="0.4000") for _ in range(5)],
            *[outcome(OutcomeLabel.CONTINUATION, confidence_score="0.9000") for _ in range(5)],
        ],
        minimum_sample_size=5,
    )

    assert diagnostic.diagnostic_label == DiagnosticLabel.NEEDS_THRESHOLD_REVIEW
    assert diagnostic.no_follow_through_rate == Decimal("0.500000")


def test_confidence_misalignment_score() -> None:
    outcomes = [
        outcome(OutcomeLabel.CONTINUATION, confidence_score="0.9000"),
        outcome(OutcomeLabel.PARTIAL_FOLLOW_THROUGH, confidence_score="0.8000"),
        outcome(OutcomeLabel.NO_FOLLOW_THROUGH, confidence_score="0.8000"),
        outcome(OutcomeLabel.REVERSAL, confidence_score="0.9000"),
    ]

    assert confidence_alignment_score(outcomes, minimum_sample_size=4) == Decimal("0.500000")


def test_aggregation_excludes_insufficient_data_from_rates() -> None:
    diagnostic = profile_diagnostic(
        [
            outcome(OutcomeLabel.CONTINUATION),
            outcome(OutcomeLabel.INSUFFICIENT_DATA, evaluation_status="insufficient_future_data"),
        ],
        minimum_sample_size=1,
    )

    assert diagnostic.sample_size == 1
    assert diagnostic.insufficient_data_count == 1
    assert diagnostic.continuation_rate == Decimal("1.000000")


def test_neutral_no_signal_does_not_distort_directional_alignment() -> None:
    directional = outcome(OutcomeLabel.CONTINUATION, confidence_score="0.9000")
    neutral = outcome(
        OutcomeLabel.NOT_DIRECTIONAL,
        bias=SignalBias.NEUTRAL,
        classification_status=SignalClassificationStatus.NO_SIGNAL,
        evaluation_status=OutcomeEvaluationStatus.SKIPPED_NOT_DIRECTIONAL,
        confidence_score="0.1000",
    )

    diagnostic = profile_diagnostic([directional, neutral], minimum_sample_size=1)

    assert diagnostic.sample_size == 1
    assert diagnostic.confidence_alignment_score == Decimal("0.900000")


def profile_diagnostic(
    outcomes: list[DiagnosticOutcome],
    minimum_sample_size: int,
) -> StrategyProfileDiagnosticResult:
    return ProfileDiagnosticCalculator().calculate_strategy_profile_diagnostic(
        workspace_id=WORKSPACE_ID,
        strategy_profile_key="default",
        strategy_profile_version="v1",
        symbol_id=None,
        timeframe=None,
        horizon_minutes=15,
        outcomes=outcomes,
        minimum_sample_size=minimum_sample_size,
        thresholds=DiagnosticThresholds(),
    )


def outcome(
    label: OutcomeLabel,
    evaluation_status: str = OutcomeEvaluationStatus.EVALUATED,
    bias: str = SignalBias.BULLISH,
    classification_status: str = SignalClassificationStatus.SIGNAL,
    confidence_score: str = "0.9000",
    symbol_id: UUID = SYMBOL_ID,
) -> DiagnosticOutcome:
    return DiagnosticOutcome(
        signal_id=uuid4(),
        strategy_profile_key="default",
        strategy_profile_version="v1",
        pattern_type="breakout",
        symbol_id=symbol_id,
        timeframe="1m",
        horizon_minutes=15,
        bias=bias,
        classification_status=classification_status,
        evaluation_status=evaluation_status,
        outcome_label=label.value,
        confidence_score=Decimal(confidence_score),
        candidate_strength=Decimal("0.7500"),
        max_favorable_move=Decimal("1"),
        max_adverse_move=Decimal("0.2"),
        net_move=Decimal("0.5"),
        max_favorable_pips=Decimal("10"),
        max_adverse_pips=Decimal("2"),
        net_pips=Decimal("5"),
        max_favorable_ticks=None,
        max_adverse_ticks=None,
        net_ticks=None,
    )
