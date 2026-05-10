from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.modules.news.models import CorrelationLabel, VolatilityReaction
from app.modules.outcomes.models import OutcomeEvaluationStatus, OutcomeLabel, SignalOutcome
from app.modules.reasoning.models import ScenarioType
from app.modules.scenario_outcomes.models import (
    ScenarioOutcomeEvaluationStatus,
    ScenarioOutcomeSupportLabel,
)

SUPPORTED_SCORE = Decimal("0.9000")
PARTIAL_SCORE = Decimal("0.6500")
CONTRADICTED_SCORE = Decimal("0.1000")
INCONCLUSIVE_SCORE = Decimal("0.4000")
NOT_APPLICABLE_SCORE = Decimal("0.0000")


@dataclass(frozen=True)
class ScenarioNewsContext:
    correlation_label: str
    volatility_reaction: str


@dataclass(frozen=True)
class ScenarioOutcomeEvaluationInput:
    scenario_type: str
    scenario_label: str
    possibility_label: str
    outcome: SignalOutcome | None
    news_contexts: list[ScenarioNewsContext]


@dataclass(frozen=True)
class ScenarioOutcomeEvaluationResult:
    evaluation_status: ScenarioOutcomeEvaluationStatus
    support_label: ScenarioOutcomeSupportLabel
    support_score: Decimal
    matched_outcome_label: str | None
    matched_evidence: list[str]
    conflicting_evidence: list[str]
    summary: str


class ScenarioOutcomeEvaluator:
    def evaluate(
        self,
        payload: ScenarioOutcomeEvaluationInput,
        support_threshold: Decimal,
    ) -> ScenarioOutcomeEvaluationResult:
        if payload.scenario_type == ScenarioType.INSUFFICIENT_CONTEXT:
            return ScenarioOutcomeEvaluationResult(
                evaluation_status=ScenarioOutcomeEvaluationStatus.NOT_APPLICABLE,
                support_label=ScenarioOutcomeSupportLabel.NOT_APPLICABLE,
                support_score=NOT_APPLICABLE_SCORE,
                matched_outcome_label=None,
                matched_evidence=["Scenario was explicitly stored as insufficient_context."],
                conflicting_evidence=[],
                summary=(
                    "Scenario outcome tracking is not applicable to insufficient-context "
                    "hypotheses."
                ),
            )
        if payload.outcome is None:
            return ScenarioOutcomeEvaluationResult(
                evaluation_status=ScenarioOutcomeEvaluationStatus.INSUFFICIENT_OUTCOME_DATA,
                support_label=ScenarioOutcomeSupportLabel.INCONCLUSIVE,
                support_score=NOT_APPLICABLE_SCORE,
                matched_outcome_label=None,
                matched_evidence=[],
                conflicting_evidence=["No stored signal outcome matched the requested horizon."],
                summary=(
                    "Scenario hypothesis could not be evaluated because no stored signal "
                    "outcome exists."
                ),
            )
        if payload.outcome.evaluation_status != OutcomeEvaluationStatus.EVALUATED:
            return ScenarioOutcomeEvaluationResult(
                evaluation_status=ScenarioOutcomeEvaluationStatus.INSUFFICIENT_OUTCOME_DATA,
                support_label=ScenarioOutcomeSupportLabel.INCONCLUSIVE,
                support_score=NOT_APPLICABLE_SCORE,
                matched_outcome_label=payload.outcome.outcome_label,
                matched_evidence=[f"Stored outcome status is {payload.outcome.evaluation_status}."],
                conflicting_evidence=[],
                summary=(
                    "Scenario hypothesis could not be evaluated because the stored outcome "
                    "is not an evaluated outcome."
                ),
            )
        result = self.evaluate_outcome(payload)
        if (
            result.support_label == ScenarioOutcomeSupportLabel.SUPPORTED
            and result.support_score < support_threshold
        ):
            return ScenarioOutcomeEvaluationResult(
                evaluation_status=result.evaluation_status,
                support_label=ScenarioOutcomeSupportLabel.PARTIALLY_SUPPORTED,
                support_score=result.support_score,
                matched_outcome_label=result.matched_outcome_label,
                matched_evidence=result.matched_evidence,
                conflicting_evidence=[
                    *result.conflicting_evidence,
                    f"Support score is below configured threshold {support_threshold}.",
                ],
                summary=result.summary,
            )
        return result

    def evaluate_outcome(
        self,
        payload: ScenarioOutcomeEvaluationInput,
    ) -> ScenarioOutcomeEvaluationResult:
        scenario_type = payload.scenario_type
        outcome_label = payload.outcome.outcome_label if payload.outcome is not None else None
        if scenario_type == ScenarioType.CONTINUATION:
            return self.evaluate_continuation(outcome_label)
        if scenario_type == ScenarioType.REVERSAL:
            return self.evaluate_reversal(outcome_label)
        if scenario_type == ScenarioType.CONSOLIDATION:
            return self.evaluate_consolidation(outcome_label)
        if scenario_type == ScenarioType.VOLATILITY_EXPANSION:
            return self.evaluate_volatility_expansion(payload)
        if scenario_type == ScenarioType.FAKEOUT_RISK:
            return self.evaluate_fakeout(payload)
        if scenario_type == ScenarioType.EVENT_DRIVEN_VOLATILITY:
            return self.evaluate_event_driven_volatility(payload)
        return ScenarioOutcomeEvaluationResult(
            evaluation_status=ScenarioOutcomeEvaluationStatus.NOT_APPLICABLE,
            support_label=ScenarioOutcomeSupportLabel.NOT_APPLICABLE,
            support_score=NOT_APPLICABLE_SCORE,
            matched_outcome_label=outcome_label,
            matched_evidence=[],
            conflicting_evidence=[f"Unsupported scenario type {scenario_type}."],
            summary="Scenario type is not applicable for deterministic outcome tracking.",
        )

    def evaluate_continuation(self, outcome_label: str | None) -> ScenarioOutcomeEvaluationResult:
        if outcome_label == OutcomeLabel.CONTINUATION:
            return supported_result(
                outcome_label,
                SUPPORTED_SCORE,
                ["Stored outcome label is continuation."],
            )
        if outcome_label == OutcomeLabel.PARTIAL_FOLLOW_THROUGH:
            return partial_result(
                outcome_label,
                ["Stored outcome label is partial_follow_through."],
                "Continuation hypothesis was partially supported by later follow-through.",
            )
        if outcome_label in {
            OutcomeLabel.REVERSAL,
            OutcomeLabel.NO_FOLLOW_THROUGH,
            OutcomeLabel.SIDEWAYS_AFTER_SIGNAL,
        }:
            return contradicted_result(
                outcome_label,
                [f"Stored outcome label is {outcome_label}."],
            )
        return inconclusive_result(
            outcome_label,
            [f"Stored outcome label is {outcome_label}."],
        )

    def evaluate_reversal(self, outcome_label: str | None) -> ScenarioOutcomeEvaluationResult:
        if outcome_label == OutcomeLabel.REVERSAL:
            return supported_result(
                outcome_label,
                SUPPORTED_SCORE,
                ["Stored outcome label is reversal."],
            )
        if outcome_label in {OutcomeLabel.CONTINUATION, OutcomeLabel.PARTIAL_FOLLOW_THROUGH}:
            return contradicted_result(
                outcome_label,
                [f"Stored outcome label is {outcome_label}."],
            )
        if outcome_label in {OutcomeLabel.NO_FOLLOW_THROUGH, OutcomeLabel.SIDEWAYS_AFTER_SIGNAL}:
            return inconclusive_result(
                outcome_label,
                [f"Stored outcome label is {outcome_label}, which does not confirm reversal."],
            )
        return inconclusive_result(
            outcome_label,
            [f"Stored outcome label is {outcome_label}."],
        )

    def evaluate_consolidation(self, outcome_label: str | None) -> ScenarioOutcomeEvaluationResult:
        if outcome_label in {OutcomeLabel.NO_FOLLOW_THROUGH, OutcomeLabel.SIDEWAYS_AFTER_SIGNAL}:
            return supported_result(
                outcome_label,
                SUPPORTED_SCORE,
                [f"Stored outcome label is {outcome_label}."],
                "Consolidation hypothesis was supported by no follow-through or sideways behavior.",
            )
        if outcome_label == OutcomeLabel.PARTIAL_FOLLOW_THROUGH:
            return partial_result(
                outcome_label,
                [
                    "Stored outcome label is partial_follow_through, "
                    "which weakens a pure consolidation read."
                ],
                "Consolidation hypothesis was only partially supported because later "
                "movement had limited follow-through.",
            )
        if outcome_label in {OutcomeLabel.CONTINUATION, OutcomeLabel.REVERSAL}:
            return contradicted_result(
                outcome_label,
                [f"Stored outcome label is {outcome_label}."],
            )
        return inconclusive_result(
            outcome_label,
            [f"Stored outcome label is {outcome_label}."],
        )

    def evaluate_volatility_expansion(
        self,
        payload: ScenarioOutcomeEvaluationInput,
    ) -> ScenarioOutcomeEvaluationResult:
        if payload.outcome is None:
            return missing_outcome_result()
        if has_elevated_volatility_context(
            payload.outcome.metadata_json,
            payload.outcome.movement_quality,
        ):
            return supported_result(
                payload.outcome.outcome_label,
                SUPPORTED_SCORE,
                ["Stored outcome metadata indicates elevated volatility."],
                "Volatility expansion hypothesis was supported by stored high-volatility "
                "outcome context.",
            )
        return inconclusive_result(
            payload.outcome.outcome_label,
            ["Stored outcome does not include elevated volatility context."],
            "Volatility expansion hypothesis remained inconclusive because no stored "
            "volatility context was available.",
        )

    def evaluate_fakeout(
        self,
        payload: ScenarioOutcomeEvaluationInput,
    ) -> ScenarioOutcomeEvaluationResult:
        if payload.outcome is None:
            return missing_outcome_result()
        breakout_context = has_breakout_context(
            payload.outcome.metadata_json,
            payload.scenario_label,
        )
        if payload.outcome.outcome_label in {OutcomeLabel.REVERSAL, OutcomeLabel.NO_FOLLOW_THROUGH}:
            score = SUPPORTED_SCORE if breakout_context else PARTIAL_SCORE
            label = (
                ScenarioOutcomeSupportLabel.SUPPORTED
                if breakout_context
                else ScenarioOutcomeSupportLabel.PARTIALLY_SUPPORTED
            )
            return ScenarioOutcomeEvaluationResult(
                evaluation_status=ScenarioOutcomeEvaluationStatus.EVALUATED,
                support_label=label,
                support_score=score,
                matched_outcome_label=payload.outcome.outcome_label,
                matched_evidence=[f"Stored outcome label is {payload.outcome.outcome_label}."],
                conflicting_evidence=(
                    [] if breakout_context else ["No stored breakout context was available."]
                ),
                summary=(
                    "Fakeout-risk hypothesis aligned with reversal or no-follow-through behavior."
                ),
            )
        if payload.outcome.outcome_label in {
            OutcomeLabel.CONTINUATION,
            OutcomeLabel.PARTIAL_FOLLOW_THROUGH,
        }:
            return contradicted_result(
                payload.outcome.outcome_label,
                [f"Stored outcome label is {payload.outcome.outcome_label}."],
            )
        return inconclusive_result(
            payload.outcome.outcome_label,
            [f"Stored outcome label is {payload.outcome.outcome_label}."],
        )

    def evaluate_event_driven_volatility(
        self,
        payload: ScenarioOutcomeEvaluationInput,
    ) -> ScenarioOutcomeEvaluationResult:
        if payload.outcome is None:
            return missing_outcome_result()
        has_news = has_news_volatility_context(payload.news_contexts)
        has_volatility = has_elevated_volatility_context(
            payload.outcome.metadata_json,
            payload.outcome.movement_quality,
        )
        if has_news and has_volatility:
            return supported_result(
                payload.outcome.outcome_label,
                SUPPORTED_SCORE,
                ["Stored news correlation and outcome volatility context are both elevated."],
                "Event-driven volatility hypothesis was supported by stored news "
                "correlation and volatility context.",
            )
        if has_news and not has_volatility:
            return inconclusive_result(
                payload.outcome.outcome_label,
                ["Stored news correlation exists but outcome volatility context is not elevated."],
                "Event-driven volatility hypothesis remained inconclusive because "
                "volatility outcome context was unavailable.",
            )
        if has_volatility and not has_news:
            return inconclusive_result(
                payload.outcome.outcome_label,
                [
                    "Stored volatility context exists but no possible or strong news "
                    "correlation was stored."
                ],
                "Event-driven volatility hypothesis remained inconclusive because news "
                "correlation was not stored.",
            )
        return inconclusive_result(
            payload.outcome.outcome_label,
            ["No stored news correlation or elevated volatility context was available."],
            "Event-driven volatility hypothesis could not be confirmed from stored "
            "outcomes and news correlations.",
        )


def supported_result(
    outcome_label: str | None,
    score: Decimal,
    evidence: list[str],
    summary: str = "Scenario hypothesis was supported by the stored signal outcome.",
) -> ScenarioOutcomeEvaluationResult:
    return ScenarioOutcomeEvaluationResult(
        evaluation_status=ScenarioOutcomeEvaluationStatus.EVALUATED,
        support_label=ScenarioOutcomeSupportLabel.SUPPORTED,
        support_score=score,
        matched_outcome_label=outcome_label,
        matched_evidence=evidence,
        conflicting_evidence=[],
        summary=summary,
    )


def missing_outcome_result() -> ScenarioOutcomeEvaluationResult:
    return ScenarioOutcomeEvaluationResult(
        evaluation_status=ScenarioOutcomeEvaluationStatus.INSUFFICIENT_OUTCOME_DATA,
        support_label=ScenarioOutcomeSupportLabel.INCONCLUSIVE,
        support_score=NOT_APPLICABLE_SCORE,
        matched_outcome_label=None,
        matched_evidence=[],
        conflicting_evidence=["No stored signal outcome matched the requested horizon."],
        summary=(
            "Scenario hypothesis could not be evaluated because no stored signal outcome exists."
        ),
    )


def partial_result(
    outcome_label: str | None,
    evidence: list[str],
    summary: str,
) -> ScenarioOutcomeEvaluationResult:
    return ScenarioOutcomeEvaluationResult(
        evaluation_status=ScenarioOutcomeEvaluationStatus.EVALUATED,
        support_label=ScenarioOutcomeSupportLabel.PARTIALLY_SUPPORTED,
        support_score=PARTIAL_SCORE,
        matched_outcome_label=outcome_label,
        matched_evidence=evidence,
        conflicting_evidence=[],
        summary=summary,
    )


def contradicted_result(
    outcome_label: str | None,
    evidence: list[str],
) -> ScenarioOutcomeEvaluationResult:
    return ScenarioOutcomeEvaluationResult(
        evaluation_status=ScenarioOutcomeEvaluationStatus.EVALUATED,
        support_label=ScenarioOutcomeSupportLabel.CONTRADICTED,
        support_score=CONTRADICTED_SCORE,
        matched_outcome_label=outcome_label,
        matched_evidence=[],
        conflicting_evidence=evidence,
        summary="Scenario hypothesis was contradicted by the stored signal outcome.",
    )


def inconclusive_result(
    outcome_label: str | None,
    evidence: list[str],
    summary: str = "Scenario hypothesis remained inconclusive against the stored signal outcome.",
) -> ScenarioOutcomeEvaluationResult:
    return ScenarioOutcomeEvaluationResult(
        evaluation_status=ScenarioOutcomeEvaluationStatus.EVALUATED,
        support_label=ScenarioOutcomeSupportLabel.INCONCLUSIVE,
        support_score=INCONCLUSIVE_SCORE,
        matched_outcome_label=outcome_label,
        matched_evidence=evidence,
        conflicting_evidence=[],
        summary=summary,
    )


def has_elevated_volatility_context(
    metadata_json: dict[str, Any],
    movement_quality: str | None,
) -> bool:
    volatility_values = collect_metadata_values(metadata_json)
    elevated_values = {
        "high",
        "elevated",
        "spike",
        "expanded",
        "expansion",
        "volatile",
        "high_volatility",
    }
    if movement_quality is not None and movement_quality.strip().lower() in elevated_values:
        return True
    return any(value in elevated_values for value in volatility_values)


def has_breakout_context(metadata_json: dict[str, Any], scenario_label: str) -> bool:
    values = collect_metadata_values(metadata_json)
    normalized_label = scenario_label.lower()
    return "breakout" in normalized_label or "breakout" in values or "breakdown" in values


def has_news_volatility_context(news_contexts: list[ScenarioNewsContext]) -> bool:
    return any(
        context.correlation_label in {CorrelationLabel.POSSIBLE, CorrelationLabel.STRONG}
        and context.volatility_reaction in {VolatilityReaction.ELEVATED, VolatilityReaction.SPIKE}
        for context in news_contexts
    )


def collect_metadata_values(value: object) -> set[str]:
    collected: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).strip().lower()
            if "volatility" in normalized_key and (
                "high" in normalized_key or "elevated" in normalized_key
            ):
                collected.add("elevated")
            if (
                "volatility" in normalized_key
                or "breakout" in normalized_key
                or "expansion" in normalized_key
            ):
                collected.add(normalized_key)
                collected.update(collect_metadata_values(item))
    elif isinstance(value, list):
        for item in value:
            collected.update(collect_metadata_values(item))
    elif isinstance(value, str):
        collected.add(value.strip().lower())
    elif isinstance(value, bool) and value:
        collected.add("true")
    return collected
