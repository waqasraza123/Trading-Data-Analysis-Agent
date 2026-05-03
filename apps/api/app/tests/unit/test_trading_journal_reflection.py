from types import SimpleNamespace
from typing import cast

from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.trading_journal.models import (
    JournalDecisionType,
    JournalReflectionLabel,
    JournalUserBias,
)
from app.modules.trading_journal.reflection import build_journal_reflection


def test_reflection_aligns_directional_note_with_observed_behavior() -> None:
    outcome = outcome_stub(
        bias=JournalUserBias.BULLISH.value,
        outcome_label=OutcomeLabel.CONTINUATION.value,
        direction_followed=True,
    )

    result = build_journal_reflection(
        decision_type=JournalDecisionType.OBSERVED.value,
        user_bias=JournalUserBias.BULLISH.value,
        outcome=outcome,
    )

    assert result.reflection_label == JournalReflectionLabel.ALIGNED_WITH_OBSERVED_OUTCOME
    assert result.metadata["reason"] == "bias_aligned"


def test_reflection_conflicts_when_note_opposes_later_observed_behavior() -> None:
    outcome = outcome_stub(
        bias=JournalUserBias.BULLISH.value,
        outcome_label=OutcomeLabel.REVERSAL.value,
        direction_followed=False,
        reversal_detected=True,
    )

    result = build_journal_reflection(
        decision_type=JournalDecisionType.OBSERVED.value,
        user_bias=JournalUserBias.BULLISH.value,
        outcome=outcome,
    )

    assert result.reflection_label == JournalReflectionLabel.CONFLICTED_WITH_OBSERVED_OUTCOME
    assert "observed behavior" in result.reflection_notes


def test_reflection_reports_insufficient_outcome_data_without_outcome() -> None:
    result = build_journal_reflection(
        decision_type=JournalDecisionType.REVIEWED.value,
        user_bias=JournalUserBias.NEUTRAL.value,
        outcome=None,
    )

    assert result.reflection_label == JournalReflectionLabel.INSUFFICIENT_OUTCOME_DATA


def test_reflection_marks_uncertain_decision_for_more_review() -> None:
    outcome = outcome_stub(
        bias=JournalUserBias.BEARISH.value,
        outcome_label=OutcomeLabel.CONTINUATION.value,
        direction_followed=True,
    )

    result = build_journal_reflection(
        decision_type=JournalDecisionType.UNCERTAIN.value,
        user_bias=JournalUserBias.BEARISH.value,
        outcome=outcome,
    )

    assert result.reflection_label == JournalReflectionLabel.NEEDS_MORE_REVIEW


def outcome_stub(
    bias: str,
    outcome_label: str,
    direction_followed: bool | None,
    reversal_detected: bool = False,
    evaluation_status: str = OutcomeEvaluationStatus.EVALUATED.value,
) -> SignalOutcome:
    return cast(
        SignalOutcome,
        SimpleNamespace(
            bias=bias,
            outcome_label=outcome_label,
            direction_followed=direction_followed,
            reversal_detected=reversal_detected,
            evaluation_status=evaluation_status,
        ),
    )
