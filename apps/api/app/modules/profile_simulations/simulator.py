from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.profile_simulations.models import StrategyProfileSimulationDecisionChangeType
from app.modules.profile_simulations.schemas import ProfileSimulationProposedConfig
from app.modules.signals.conflicts import resolve_conflicts
from app.modules.signals.models import Signal, SignalBias, SignalClassificationStatus
from app.modules.signals.service import SignalClassificationService, dominant_rejection_reason
from app.modules.strategy_profiles.models import StrategyProfile


@dataclass(frozen=True)
class SimulatedSignalDecision:
    classification_status: str
    bias: str
    pattern_type: str | None
    confidence_score: Decimal | None
    decision_change_type: StrategyProfileSimulationDecisionChangeType
    reason_json: dict[str, object]


class StrategyProfileSandboxSimulator:
    def __init__(self, classifier: SignalClassificationService) -> None:
        self.classifier = classifier

    def simulate_signal(
        self,
        signal: Signal,
        base_profile: StrategyProfile,
        proposed_config: ProfileSimulationProposedConfig,
        candidates: list[PatternCandidate],
        feature_snapshot: FeatureSnapshot | None,
        indicator_snapshot: IndicatorSnapshot | None,
        outcomes: list[SignalOutcome],
    ) -> SimulatedSignalDecision:
        if not candidates:
            return SimulatedSignalDecision(
                classification_status=SignalClassificationStatus.NO_SIGNAL.value,
                bias=SignalBias.NEUTRAL.value,
                pattern_type=None,
                confidence_score=Decimal("0.0000"),
                decision_change_type=StrategyProfileSimulationDecisionChangeType.NO_CANDIDATE,
                reason_json={
                    "reason": "no_candidate",
                    "message": "No persisted pattern candidates were available for simulation.",
                    "observedOutcomes": serialize_outcomes(outcomes),
                },
            )
        hypothetical_profile = build_hypothetical_profile(base_profile, proposed_config)
        evaluations, rejections = self.classifier.evaluate_candidates(
            profiles=[hypothetical_profile],
            candidates=candidates,
            features=feature_snapshot.features_json if feature_snapshot is not None else None,
            indicators=indicator_snapshot.indicators_json if indicator_snapshot is not None else None,
        )
        if evaluations:
            decision = resolve_conflicts(evaluations)
            selected = decision.selected_evaluation
            pattern_type = selected.candidate.pattern_type if selected is not None else None
            confidence_score = (
                selected.confidence.confidence_score if selected is not None else Decimal("0.0000")
            )
            simulated_status = decision.classification_status.value
            simulated_bias = decision.bias.value
        else:
            selected = None
            reason = dominant_rejection_reason(rejections)
            simulated_status = (
                SignalClassificationStatus.INSUFFICIENT_EVIDENCE.value
                if reason in {"low_data_quality", "insufficient_evidence"}
                else SignalClassificationStatus.NO_SIGNAL.value
            )
            simulated_bias = SignalBias.NEUTRAL.value
            pattern_type = None
            confidence_score = Decimal("0.0000")
        return SimulatedSignalDecision(
            classification_status=simulated_status,
            bias=simulated_bias,
            pattern_type=pattern_type,
            confidence_score=confidence_score,
            decision_change_type=classify_decision_change(
                signal=signal,
                simulated_status=simulated_status,
                simulated_bias=simulated_bias,
                simulated_pattern_type=pattern_type,
                simulated_confidence_score=confidence_score,
            ),
            reason_json={
                "eligibleCandidateCount": len(evaluations),
                "rejectedCandidateCount": len(rejections),
                "dominantRejectionReason": dominant_rejection_reason(rejections),
                "selectedCandidateId": str(selected.candidate.id) if selected is not None else None,
                "selectedProfileKey": hypothetical_profile.key,
                "summary": (
                    resolve_conflicts(evaluations).summary
                    if evaluations
                    else "No candidate passed hypothetical config filters."
                ),
                "rejections": [
                    {
                        "profileKey": rejection.profile_key,
                        "patternType": rejection.pattern_type,
                        "reasonCode": rejection.reason_code,
                        "message": rejection.message,
                        "candidateStrength": str(rejection.candidate_strength),
                    }
                    for rejection in rejections[:25]
                ],
                "observedOutcomes": serialize_outcomes(outcomes),
            },
        )


def build_hypothetical_profile(
    base_profile: StrategyProfile,
    proposed_config: ProfileSimulationProposedConfig,
) -> StrategyProfile:
    profile = StrategyProfile(
        id=base_profile.id,
        key=base_profile.key,
        name=base_profile.name,
        description=base_profile.description,
        version=base_profile.version,
        is_active=base_profile.is_active,
        allowed_patterns_json=list(base_profile.allowed_patterns_json),
        excluded_patterns_json=list(base_profile.excluded_patterns_json),
        minimum_candidate_strength=base_profile.minimum_candidate_strength,
        minimum_confidence=base_profile.minimum_confidence,
        component_weights_json=dict(base_profile.component_weights_json),
        risk_filters_json=dict(base_profile.risk_filters_json),
        no_signal_rules_json=dict(base_profile.no_signal_rules_json),
    )
    if proposed_config.minimum_candidate_strength is not None:
        profile.minimum_candidate_strength = proposed_config.minimum_candidate_strength
    if proposed_config.minimum_confidence is not None:
        profile.minimum_confidence = proposed_config.minimum_confidence
    if proposed_config.component_weights_json is not None:
        profile.component_weights_json = json_safe_dict(proposed_config.component_weights_json)
    if proposed_config.risk_filters_json is not None:
        profile.risk_filters_json = json_safe_dict(proposed_config.risk_filters_json)
    if proposed_config.no_signal_rules_json is not None:
        profile.no_signal_rules_json = json_safe_dict(proposed_config.no_signal_rules_json)
    if proposed_config.allowed_patterns_json is not None:
        profile.allowed_patterns_json = list(proposed_config.allowed_patterns_json)
    if proposed_config.excluded_patterns_json is not None:
        profile.excluded_patterns_json = list(proposed_config.excluded_patterns_json)
    return profile


def classify_decision_change(
    signal: Signal,
    simulated_status: str,
    simulated_bias: str,
    simulated_pattern_type: str | None,
    simulated_confidence_score: Decimal | None,
) -> StrategyProfileSimulationDecisionChangeType:
    original_is_signal = signal.classification_status == SignalClassificationStatus.SIGNAL.value
    simulated_is_signal = simulated_status == SignalClassificationStatus.SIGNAL.value
    if not original_is_signal and simulated_is_signal:
        return StrategyProfileSimulationDecisionChangeType.INCLUDED
    if original_is_signal and not simulated_is_signal:
        return StrategyProfileSimulationDecisionChangeType.EXCLUDED
    if signal.bias != simulated_bias:
        return StrategyProfileSimulationDecisionChangeType.BIAS_CHANGED
    if signal.pattern_type != simulated_pattern_type:
        return StrategyProfileSimulationDecisionChangeType.PATTERN_CHANGED
    if simulated_confidence_score is not None and signal.confidence_score != simulated_confidence_score:
        return StrategyProfileSimulationDecisionChangeType.CONFIDENCE_CHANGED
    return StrategyProfileSimulationDecisionChangeType.UNCHANGED


def summarize_results(
    decisions: list[SimulatedSignalDecision],
    outcomes_by_signal: Mapping[str, list[SignalOutcome]],
) -> dict[str, object]:
    decision_counts = Counter(decision.decision_change_type.value for decision in decisions)
    outcome_counts: Counter[str] = Counter()
    for outcomes in outcomes_by_signal.values():
        for outcome in outcomes:
            outcome_counts[outcome.outcome_label] += 1
    return {
        "decisionChanges": dict(decision_counts),
        "outcomeLabels": dict(outcome_counts),
        "calibrationReview": calibration_review_summary(decisions),
    }


def calibration_review_summary(decisions: list[SimulatedSignalDecision]) -> dict[str, object]:
    changed = [
        decision
        for decision in decisions
        if decision.decision_change_type != StrategyProfileSimulationDecisionChangeType.UNCHANGED
    ]
    return {
        "changedDecisionCount": len(changed),
        "reviewSuggested": bool(changed),
        "reviewReason": (
            "Hypothetical config changed included/excluded historical cases."
            if changed
            else "Hypothetical config matched sampled historical cases."
        ),
    }


def serialize_outcomes(outcomes: list[SignalOutcome]) -> list[dict[str, object]]:
    return [
        {
            "outcomeLabel": outcome.outcome_label,
            "horizonMinutes": outcome.horizon_minutes,
            "evaluationStatus": outcome.evaluation_status,
            "directionFollowed": outcome.direction_followed,
            "reversalDetected": outcome.reversal_detected,
            "movementQuality": outcome.movement_quality,
        }
        for outcome in outcomes
    ]


def json_safe_dict(values: Mapping[str, Any]) -> dict[str, object]:
    return {str(key): json_safe_value(value) for key, value in values.items()}


def json_safe_value(value: Any) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return json_safe_dict(value)
    if isinstance(value, list):
        return [json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
