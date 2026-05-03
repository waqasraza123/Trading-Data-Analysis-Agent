from decimal import Decimal
from uuid import UUID, uuid4

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel
from app.modules.pattern_attribution.calculator import (
    AttributionThresholds,
    CandidateAttributionObservation,
    PatternAttributionAggregate,
    PatternAttributionCalculator,
    candidate_behavior,
)
from app.modules.pattern_attribution.models import PatternAttributionLabel
from app.modules.signals.models import SignalClassificationStatus

WORKSPACE_ID = uuid4()
SYMBOL_ID = uuid4()


def test_selected_candidate_with_follow_through_gets_strong_selected_label() -> None:
    selected = [
        observation(
            behavior="selected",
            outcome_label=OutcomeLabel.CONTINUATION.value,
            selected_confidence=Decimal("0.8000"),
        )
        for _ in range(5)
    ]

    result = calculator_result(selected, minimum_sample_size=5)

    assert result.attribution_label == PatternAttributionLabel.STRONG_SELECTED_BEHAVIOR
    assert result.selected_count == 5
    assert result.continuation_rate == Decimal("1.000000")
    assert result.average_selected_confidence == Decimal("0.800000")


def test_high_rejection_rate_gets_often_rejected_label() -> None:
    observations = [
        *[
            observation(behavior="rejected", outcome_label=None, selected_confidence=None)
            for _ in range(6)
        ],
        *[
            observation(
                behavior="selected",
                outcome_label=OutcomeLabel.CONTINUATION.value,
                selected_confidence=Decimal("0.7000"),
            )
            for _ in range(4)
        ],
    ]

    result = calculator_result(observations, minimum_sample_size=5)

    assert result.attribution_label == PatternAttributionLabel.OFTEN_REJECTED
    assert result.rejected_count == 6
    assert result.metadata_json["rejectedRate"] == "0.600000"


def test_blocked_fakeout_no_directional_outcome_gets_blocking_label() -> None:
    observations = [
        observation(
            pattern_type="fakeout",
            behavior="blocked",
            outcome_label=OutcomeLabel.SIDEWAYS_AFTER_SIGNAL.value,
            evaluation_status=OutcomeEvaluationStatus.SKIPPED_NOT_DIRECTIONAL.value,
            selected_confidence=Decimal("0.7600"),
        )
        for _ in range(5)
    ]

    result = calculator_result(observations, minimum_sample_size=5)

    assert result.attribution_label == PatternAttributionLabel.BLOCKING_EFFECTIVE
    assert result.blocked_count == 5
    assert result.no_follow_through_count == 5


def test_reversal_outcomes_get_reversal_prone_label() -> None:
    observations = [
        *[
            observation(
                behavior="selected",
                outcome_label=OutcomeLabel.REVERSAL.value,
                selected_confidence=Decimal("0.8500"),
            )
            for _ in range(4)
        ],
        *[
            observation(
                behavior="selected",
                outcome_label=OutcomeLabel.CONTINUATION.value,
                selected_confidence=Decimal("0.8500"),
            )
            for _ in range(6)
        ],
    ]

    result = calculator_result(observations, minimum_sample_size=5)

    assert result.attribution_label == PatternAttributionLabel.REVERSAL_PRONE
    assert result.reversal_rate == Decimal("0.400000")


def test_candidate_behavior_detects_selected_blocker() -> None:
    candidate_id = uuid4()

    behavior = candidate_behavior(
        candidate_id=candidate_id,
        pattern_type="low_volatility_chop",
        signal_selected_candidate_id=candidate_id,
        signal_classification_status=SignalClassificationStatus.NO_SIGNAL.value,
        signal_no_signal_reason="chop_or_sideways_market",
        signal_risk_note_codes=set(),
    )

    assert behavior == "blocked"


def test_candidate_behavior_detects_rejected_candidate() -> None:
    behavior = candidate_behavior(
        candidate_id=uuid4(),
        pattern_type="bullish_breakout",
        signal_selected_candidate_id=uuid4(),
        signal_classification_status=SignalClassificationStatus.SIGNAL.value,
        signal_no_signal_reason=None,
        signal_risk_note_codes=set(),
    )

    assert behavior == "rejected"


def calculator_result(
    observations: list[CandidateAttributionObservation],
    minimum_sample_size: int,
) -> PatternAttributionAggregate:
    return PatternAttributionCalculator().build_results(
        observations=observations,
        minimum_sample_size=minimum_sample_size,
        thresholds=AttributionThresholds(),
    )[0]


def observation(
    behavior: str,
    outcome_label: str | None,
    selected_confidence: Decimal | None,
    pattern_type: str = "bullish_breakout",
    evaluation_status: str | None = OutcomeEvaluationStatus.EVALUATED.value,
    candidate_id: UUID | None = None,
) -> CandidateAttributionObservation:
    return CandidateAttributionObservation(
        workspace_id=WORKSPACE_ID,
        candidate_id=candidate_id or uuid4(),
        signal_id=uuid4(),
        pattern_type=pattern_type,
        strategy_profile_key="breakout_continuation",
        symbol_id=SYMBOL_ID,
        timeframe="1m",
        horizon_minutes=15,
        strength_score=Decimal("0.7500"),
        selected_confidence=selected_confidence,
        behavior=behavior,
        outcome_label=outcome_label,
        evaluation_status=evaluation_status if outcome_label is not None else None,
        missing_outcome=outcome_label is None and behavior in {"selected", "blocked"},
    )
