from dataclasses import dataclass

from app.modules.outcomes.models import (
    OutcomeEvaluationStatus,
    OutcomeLabel,
    SignalOutcome,
)
from app.modules.trading_journal.models import (
    JournalDecisionType,
    JournalReflectionLabel,
    JournalUserBias,
)

DIRECTIONAL_BIASES = {JournalUserBias.BULLISH.value, JournalUserBias.BEARISH.value}
NON_DIRECTIONAL_OUTCOMES = {
    OutcomeLabel.NO_FOLLOW_THROUGH.value,
    OutcomeLabel.SIDEWAYS_AFTER_SIGNAL.value,
    OutcomeLabel.NOT_DIRECTIONAL.value,
}
INSUFFICIENT_OUTCOMES = {
    OutcomeLabel.INSUFFICIENT_DATA.value,
    OutcomeLabel.FAILED.value,
}


@dataclass(frozen=True)
class JournalReflectionResult:
    reflection_label: JournalReflectionLabel
    reflection_notes: str
    lessons: list[str]
    metadata: dict[str, object]


def build_journal_reflection(
    decision_type: str,
    user_bias: str | None,
    outcome: SignalOutcome | None,
) -> JournalReflectionResult:
    if outcome is None:
        return JournalReflectionResult(
            reflection_label=JournalReflectionLabel.INSUFFICIENT_OUTCOME_DATA,
            reflection_notes=(
                "No deterministic outcome is available yet for this journal entry. "
                "Review again after later observed behavior has been evaluated."
            ),
            lessons=[
                "Keep the user decision note available for comparison once outcome data exists.",
                "Use the review again after deterministic outcome evaluation completes.",
            ],
            metadata={"reason": "outcome_missing"},
        )

    if (
        outcome.evaluation_status != OutcomeEvaluationStatus.EVALUATED.value
        or outcome.outcome_label in INSUFFICIENT_OUTCOMES
    ):
        return JournalReflectionResult(
            reflection_label=JournalReflectionLabel.INSUFFICIENT_OUTCOME_DATA,
            reflection_notes=(
                "The linked deterministic outcome does not contain enough later observed "
                "behavior for a useful journal comparison."
            ),
            lessons=[
                "Wait for sufficient final-candle evidence before drawing a journal lesson.",
                "Keep the reflection open until deterministic outcome data is available.",
            ],
            metadata={
                "reason": "outcome_not_evaluable",
                "evaluationStatus": outcome.evaluation_status,
                "outcomeLabel": outcome.outcome_label,
            },
        )

    if decision_type == JournalDecisionType.UNCERTAIN.value:
        return JournalReflectionResult(
            reflection_label=JournalReflectionLabel.NEEDS_MORE_REVIEW,
            reflection_notes=(
                "The journal decision note was marked uncertain. Compare the note with the "
                "outcome details and add a clearer reflection if the setup is reviewed later."
            ),
            lessons=[
                "Record the specific observation that made the setup uncertain.",
                "Separate observation quality from later observed behavior.",
            ],
            metadata={
                "reason": "uncertain_decision",
                "outcomeLabel": outcome.outcome_label,
            },
        )

    observed_bias = infer_observed_bias(outcome)
    if user_bias not in DIRECTIONAL_BIASES or observed_bias is None:
        return JournalReflectionResult(
            reflection_label=JournalReflectionLabel.INCONCLUSIVE,
            reflection_notes=(
                "The journal note or deterministic outcome is not directional enough for an "
                "alignment comparison."
            ),
            lessons=[
                "Use neutral or unclear labels when the setup context was not directional.",
                "Review whether the note captured the evidence that mattered at the time.",
            ],
            metadata={
                "reason": "non_directional_comparison",
                "observedBias": observed_bias,
                "userBias": user_bias,
                "outcomeLabel": outcome.outcome_label,
            },
        )

    if user_bias == observed_bias:
        return JournalReflectionResult(
            reflection_label=JournalReflectionLabel.ALIGNED_WITH_OBSERVED_OUTCOME,
            reflection_notes=(
                "The user decision note was directionally aligned with the later observed "
                "behavior recorded by the deterministic outcome."
            ),
            lessons=[
                "Identify which setup context details supported the aligned observation.",
                "Reuse the same evidence checklist when reviewing similar setups.",
            ],
            metadata={
                "reason": "bias_aligned",
                "observedBias": observed_bias,
                "userBias": user_bias,
                "outcomeLabel": outcome.outcome_label,
            },
        )

    return JournalReflectionResult(
        reflection_label=JournalReflectionLabel.CONFLICTED_WITH_OBSERVED_OUTCOME,
        reflection_notes=(
            "The user decision note conflicted with the later observed behavior recorded by "
            "the deterministic outcome."
        ),
        lessons=[
            "Review which evidence was over-weighted in the original observation.",
            "Compare the note against final-candle behavior before updating the lesson.",
        ],
        metadata={
            "reason": "bias_conflicted",
            "observedBias": observed_bias,
            "userBias": user_bias,
            "outcomeLabel": outcome.outcome_label,
        },
    )


def infer_observed_bias(outcome: SignalOutcome) -> str | None:
    if outcome.outcome_label in NON_DIRECTIONAL_OUTCOMES:
        return None
    if (
        outcome.outcome_label
        in {
            OutcomeLabel.CONTINUATION.value,
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH.value,
        }
        and outcome.direction_followed
    ):
        return outcome.bias if outcome.bias in DIRECTIONAL_BIASES else None
    if outcome.outcome_label == OutcomeLabel.REVERSAL.value or outcome.reversal_detected:
        if outcome.bias == JournalUserBias.BULLISH.value:
            return JournalUserBias.BEARISH.value
        if outcome.bias == JournalUserBias.BEARISH.value:
            return JournalUserBias.BULLISH.value
    return None
