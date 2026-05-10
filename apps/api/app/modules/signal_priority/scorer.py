from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from app.config import Settings
from app.modules.action_plans.models import ReasoningActionItem
from app.modules.cohort_drift.models import CohortDriftResult
from app.modules.confidence_calibration.models import ConfidenceCalibrationBin
from app.modules.cross_asset_context.models import CrossAssetContextResult
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.historical_cases.models import HistoricalCaseSearch, HistoricalCaseVector
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityRun,
    ShadowClassificationResult,
)
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.outcomes.models import SignalOutcome
from app.modules.setup_context.models import SetupContext
from app.modules.signal_priority.models import SignalPriorityLabel, SignalReviewBucket
from app.modules.signal_priority.repository import SignalPriorityArtifacts
from app.modules.signals.models import Signal, SignalEvidence
from app.modules.timeframe_aggregation.models import MultiTimeframeContext

ZERO = Decimal("0")
ONE = Decimal("1")
FOUR_PLACES = Decimal("0.0001")
COMPONENT_WEIGHTS = {
    "confidence_component": Decimal("0.16"),
    "setup_quality_component": Decimal("0.16"),
    "freshness_component": Decimal("0.12"),
    "data_quality_component": Decimal("0.12"),
    "timeframe_agreement_component": Decimal("0.10"),
    "cross_asset_component": Decimal("0.08"),
    "historical_reliability_component": Decimal("0.08"),
    "readiness_component": Decimal("0.10"),
    "quality_gate_component": Decimal("0.04"),
    "outcome_reliability_component": Decimal("0.04"),
}
RISK_PENALTY_VALUES = {
    "info": Decimal("0.00"),
    "low": Decimal("0.02"),
    "medium": Decimal("0.05"),
    "high": Decimal("0.08"),
    "critical": Decimal("0.18"),
}
SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(frozen=True)
class ComponentScore:
    score: Decimal
    reason: str
    source_artifact: str
    missing: bool = False


@dataclass(frozen=True)
class SignalPriorityDraft:
    priority_score: Decimal
    priority_label: SignalPriorityLabel
    review_bucket: SignalReviewBucket
    component_scores_json: dict[str, object]
    penalties_json: list[dict[str, object]]
    boosters_json: list[dict[str, object]]
    reasons_json: list[dict[str, object]]
    warnings_json: list[dict[str, object]]


class SignalPriorityScorer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def score(self, artifacts: SignalPriorityArtifacts) -> SignalPriorityDraft:
        components = {
            "confidence_component": confidence_component(artifacts.signal),
            "setup_quality_component": setup_quality_component(artifacts.setup_context),
            "freshness_component": freshness_component(artifacts.market_memory),
            "data_quality_component": data_quality_component(artifacts.data_quality_run),
            "timeframe_agreement_component": timeframe_agreement_component(
                artifacts.multi_timeframe_context,
                artifacts.setup_context,
            ),
            "cross_asset_component": cross_asset_component(artifacts.cross_asset_results),
            "historical_reliability_component": historical_reliability_component(
                artifacts.historical_case_vector,
                artifacts.historical_case_search,
            ),
            "readiness_component": readiness_component(artifacts.decision_readiness),
            "quality_gate_component": quality_gate_component(
                artifacts.intelligence_quality_run,
                artifacts.intelligence_quality_findings,
                artifacts.shadow_classifications,
            ),
            "outcome_reliability_component": outcome_reliability_component(
                artifacts.outcomes,
                artifacts.confidence_calibration_bin,
                artifacts.cohort_drift_results,
            ),
        }
        weighted_score = sum(
            components[name].score * COMPONENT_WEIGHTS[name] for name in COMPONENT_WEIGHTS
        )
        penalties = collect_penalties(artifacts, self.settings)
        boosters = collect_boosters(artifacts, components)
        final_score = decimal_score(
            weighted_score - sum_decimal_values(penalties) + sum_decimal_values(boosters)
        )
        review_bucket = review_bucket_for(artifacts, components, final_score)
        priority_label = priority_label_for(artifacts, final_score, review_bucket, self.settings)
        warnings = collect_warnings(artifacts, components)
        reasons = collect_reasons(artifacts, components, final_score, priority_label, review_bucket)
        return SignalPriorityDraft(
            priority_score=final_score,
            priority_label=priority_label,
            review_bucket=review_bucket,
            component_scores_json=to_json_value(
                {
                    name: {
                        "score": component.score,
                        "weight": COMPONENT_WEIGHTS[name],
                        "reason": component.reason,
                        "sourceArtifact": component.source_artifact,
                        "missing": component.missing,
                    }
                    for name, component in components.items()
                }
            ),
            penalties_json=to_json_value(penalties),
            boosters_json=to_json_value(boosters),
            reasons_json=to_json_value(reasons),
            warnings_json=to_json_value(warnings),
        )


def confidence_component(signal: Signal) -> ComponentScore:
    return ComponentScore(
        score=clamp(Decimal(signal.confidence_score)),
        reason="Signal confidence contributes to review priority.",
        source_artifact="signals",
    )


def setup_quality_component(setup_context: SetupContext | None) -> ComponentScore:
    if setup_context is None:
        return missing_component("Setup context is not available.", "setup_contexts")
    return ComponentScore(
        score=clamp(Decimal(setup_context.setup_quality_score)),
        reason=f"Setup context label is {setup_context.setup_quality_label}.",
        source_artifact="setup_contexts",
    )


def freshness_component(memory: RollingMarketStateSnapshot | None) -> ComponentScore:
    if memory is None:
        return missing_component(
            "Market memory freshness context is not available.",
            "market_memory",
        )
    score = {
        "fresh": Decimal("0.9500"),
        "delayed": Decimal("0.6500"),
        "stale": Decimal("0.2500"),
        "no_data": Decimal("0.1000"),
        "unknown": Decimal("0.4500"),
    }.get(memory.freshness_label, Decimal("0.4500"))
    return ComponentScore(
        score=score,
        reason=f"Market memory freshness label is {memory.freshness_label}.",
        source_artifact="rolling_market_state_snapshots",
    )


def data_quality_component(data_quality_run: DataQualityRun | None) -> ComponentScore:
    if data_quality_run is None:
        return missing_component("Data quality run is not available.", "data_quality_runs")
    return ComponentScore(
        score=clamp(Decimal(data_quality_run.quality_score)),
        reason=f"Data quality label is {data_quality_run.quality_label}.",
        source_artifact="data_quality_runs",
    )


def timeframe_agreement_component(
    context: MultiTimeframeContext | None,
    setup_context: SetupContext | None,
) -> ComponentScore:
    if context is not None:
        return ComponentScore(
            score=clamp(Decimal(context.agreement_score)),
            reason=f"Multi-timeframe agreement label is {context.agreement_label}.",
            source_artifact="multi_timeframe_contexts",
        )
    if setup_context is not None:
        value = setup_context.timeframe_agreement_json.get("agreementScore")
        if value is not None:
            return ComponentScore(
                score=clamp(Decimal(str(value))),
                reason="Setup context includes multi-timeframe agreement.",
                source_artifact="setup_contexts.timeframe_agreement_json",
            )
    return missing_component(
        "Multi-timeframe context is not available.",
        "multi_timeframe_contexts",
    )


def cross_asset_component(results: list[CrossAssetContextResult]) -> ComponentScore:
    if not results:
        return missing_component("Cross-asset context is not available.", "cross_asset_context")
    scores = [cross_asset_result_score(result) for result in results]
    average = sum(scores, ZERO) / Decimal(len(scores))
    labels = sorted({result.alignment_label for result in results})
    return ComponentScore(
        score=decimal_score(average),
        reason=f"Cross-asset labels: {', '.join(labels)}.",
        source_artifact="cross_asset_context_results",
    )


def historical_reliability_component(
    vector: HistoricalCaseVector | None,
    search: HistoricalCaseSearch | None,
) -> ComponentScore:
    if vector is None and search is None:
        return missing_component("Historical case context is not available.", "historical_cases")
    scores: list[Decimal] = []
    if search is not None and search.results_json:
        scores.append(historical_search_score(search.results_json))
    if vector is not None and vector.outcome_summary_json:
        scores.append(outcome_summary_score(vector.outcome_summary_json))
    if not scores:
        return ComponentScore(
            score=Decimal("0.5500"),
            reason="Historical context is available without outcome reliability details.",
            source_artifact="historical_case_vectors",
        )
    return ComponentScore(
        score=decimal_score(sum(scores, ZERO) / Decimal(len(scores))),
        reason="Historical case similarity and outcome reliability are available.",
        source_artifact="historical_cases",
    )


def readiness_component(readiness: DecisionReadinessAssessment | None) -> ComponentScore:
    if readiness is None:
        return missing_component(
            "Decision readiness assessment is not available.",
            "decision_readiness_assessments",
        )
    score = {
        "ready": Decimal("0.9000"),
        "review_recommended": Decimal("0.6500"),
        "blocked": Decimal("0.1500"),
        "insufficient_context": Decimal("0.3500"),
    }.get(readiness.readiness_label, Decimal("0.5000"))
    return ComponentScore(
        score=score,
        reason=f"Decision readiness label is {readiness.readiness_label}.",
        source_artifact="decision_readiness_assessments",
    )


def quality_gate_component(
    quality_run: IntelligenceQualityRun | None,
    findings: list[IntelligenceQualityFinding],
    shadow_classifications: list[ShadowClassificationResult],
) -> ComponentScore:
    if quality_run is None:
        return missing_component(
            "Intelligence quality gate context is not available.",
            "intelligence_quality_runs",
        )
    score = clamp(Decimal(quality_run.quality_score))
    if has_severity(findings, "critical"):
        score = min(score, Decimal("0.1000"))
    elif has_shadow_disagreement(shadow_classifications):
        score = min(score, Decimal("0.4500"))
    return ComponentScore(
        score=score,
        reason=f"Intelligence quality label is {quality_run.quality_label}.",
        source_artifact="intelligence_quality_runs",
    )


def outcome_reliability_component(
    outcomes: list[SignalOutcome],
    calibration_bin: ConfidenceCalibrationBin | None,
    drift_results: list[CohortDriftResult],
) -> ComponentScore:
    scores: list[Decimal] = []
    sources: list[str] = []
    if outcomes:
        scores.append(outcomes_score(outcomes))
        sources.append("signal_outcomes")
    if calibration_bin is not None:
        scores.append(clamp(Decimal(calibration_bin.confidence_alignment_score)))
        sources.append("confidence_calibration_bins")
    if drift_results:
        scores.append(cohort_drift_score(drift_results))
        sources.append("cohort_drift_results")
    if not scores:
        return missing_component(
            "Recent outcome reliability context is not available.",
            "outcomes_confidence_calibration_cohort_drift",
        )
    return ComponentScore(
        score=decimal_score(sum(scores, ZERO) / Decimal(len(scores))),
        reason="Outcome reliability/profile diagnostics are available.",
        source_artifact=", ".join(sources),
    )


def collect_penalties(
    artifacts: SignalPriorityArtifacts,
    settings: Settings,
) -> list[dict[str, object]]:
    penalties: list[dict[str, object]] = []
    if has_stale_data(artifacts):
        penalties.append(
            penalty(
                "stale_data",
                settings.signal_priority_stale_penalty,
                "Stale data lowers review priority confidence.",
            )
        )
    if has_low_data_quality(artifacts):
        penalties.append(
            penalty(
                "low_data_quality",
                Decimal("0.1800"),
                "Low data quality requires confirmation before review context is useful.",
            )
        )
    if has_conflicting_evidence(artifacts):
        penalties.append(
            penalty(
                "conflicting_evidence",
                settings.signal_priority_conflict_penalty,
                "Conflicting evidence requires review.",
            )
        )
    if is_not_directional(artifacts.signal):
        penalties.append(
            penalty(
                "no_signal_neutral_unclear",
                Decimal("0.3500"),
                "No directional signal or unclear context is ranked as avoid condition.",
            )
        )
    if has_blocked_readiness(artifacts.decision_readiness):
        penalties.append(
            penalty(
                "unresolved_critical_review",
                Decimal("0.3000"),
                "Decision readiness blockers require review first.",
            )
        )
    if has_failed_quality_safety(artifacts):
        penalties.append(
            penalty(
                "failed_grounding_safety",
                Decimal("0.3000"),
                "Failed grounding or safety findings require review.",
            )
        )
    if has_pending_data_recovery(artifacts):
        penalties.append(
            penalty(
                "pending_data_recovery",
                Decimal("0.1500"),
                "Pending data recovery reduces priority score until context refreshes.",
            )
        )
    for risk_note in artifacts.risk_notes:
        value = RISK_PENALTY_VALUES.get(risk_note.severity, Decimal("0.0300"))
        if value > ZERO:
            penalties.append(
                penalty(
                    f"risk_note_{risk_note.severity}",
                    value,
                    safe_text(risk_note.message),
                    source="signal_risk_notes",
                    code=risk_note.code,
                )
            )
    return penalties


def collect_boosters(
    artifacts: SignalPriorityArtifacts,
    components: dict[str, ComponentScore],
) -> list[dict[str, object]]:
    boosters: list[dict[str, object]] = []
    if Decimal(artifacts.signal.confidence_score) >= Decimal("0.7500"):
        boosters.append(booster("high_confidence", Decimal("0.0500"), "High signal confidence."))
    if components["setup_quality_component"].score >= Decimal("0.7500"):
        boosters.append(booster("strong_setup_context", Decimal("0.0500"), "Strong setup context."))
    if components["freshness_component"].score >= Decimal("0.9000"):
        boosters.append(booster("fresh_data", Decimal("0.0400"), "Fresh data context."))
    if components["timeframe_agreement_component"].score >= Decimal("0.7500"):
        boosters.append(
            booster(
                "aligned_timeframe_context",
                Decimal("0.0400"),
                "Aligned multi-timeframe context.",
            )
        )
    if components["data_quality_component"].score >= Decimal("0.8500"):
        boosters.append(
            booster("acceptable_data_quality", Decimal("0.0300"), "Acceptable data quality.")
        )
    if components["historical_reliability_component"].score >= Decimal("0.7000"):
        boosters.append(
            booster(
                "historically_stable_profile",
                Decimal("0.0300"),
                "Historical profile or pattern is stable.",
            )
        )
    if has_recent_follow_through(artifacts.outcomes):
        boosters.append(
            booster(
                "recent_observed_follow_through",
                Decimal("0.0300"),
                "Recent observed follow-through is available.",
            )
        )
    if has_pending_human_review(artifacts.action_items):
        boosters.append(
            booster(
                "pending_action_urgency",
                Decimal("0.0500"),
                "Pending human review action increases review priority.",
            )
        )
    return boosters


def collect_warnings(
    artifacts: SignalPriorityArtifacts,
    components: dict[str, ComponentScore],
) -> list[dict[str, object]]:
    warnings = [
        {
            "code": "missing_context",
            "message": component.reason,
            "sourceArtifact": component.source_artifact,
        }
        for component in components.values()
        if component.missing
    ]
    if artifacts.analysis_run is None:
        warnings.append(
            {
                "code": "missing_context",
                "message": "Analysis run context is not available.",
                "sourceArtifact": "analysis_runs",
            }
        )
    return warnings


def collect_reasons(
    artifacts: SignalPriorityArtifacts,
    components: dict[str, ComponentScore],
    final_score: Decimal,
    priority_label: SignalPriorityLabel,
    review_bucket: SignalReviewBucket,
) -> list[dict[str, object]]:
    reasons = [
        {
            "code": "priority_score",
            "message": f"Review priority score is {final_score}.",
            "source": "signal_priority",
        },
        {
            "code": "priority_label",
            "message": f"Review priority label is {priority_label.value}.",
            "source": "signal_priority",
        },
        {
            "code": "review_bucket",
            "message": f"Review bucket is {review_bucket.value}.",
            "source": "signal_priority",
        },
    ]
    strongest = sorted(components.items(), key=lambda item: item[1].score, reverse=True)[:3]
    reasons.extend(
        {
            "code": name,
            "message": component.reason,
            "source": component.source_artifact,
            "score": component.score,
        }
        for name, component in strongest
    )
    if artifacts.setup_context is not None and artifacts.setup_context.avoid_reasons_json:
        reasons.append(
            {
                "code": "avoid_condition",
                "message": "Setup context includes avoid condition.",
                "source": "setup_contexts",
            }
        )
    return reasons


def review_bucket_for(
    artifacts: SignalPriorityArtifacts,
    components: dict[str, ComponentScore],
    final_score: Decimal,
) -> SignalReviewBucket:
    if has_review_required(artifacts, final_score):
        return SignalReviewBucket.REVIEW_REQUIRED
    if has_stale_data(artifacts) or has_low_data_quality(artifacts):
        return SignalReviewBucket.STALE_OR_DATA_ISSUE
    if has_conflicting_evidence(artifacts):
        return SignalReviewBucket.CONFLICTED
    if is_not_directional(artifacts.signal) or has_avoid_condition(artifacts.setup_context):
        return SignalReviewBucket.AVOID_OR_NO_DIRECTIONAL_SIGNAL
    if needs_confirmation(artifacts, components):
        return SignalReviewBucket.NEEDS_CONFIRMATION
    return SignalReviewBucket.HIGH_QUALITY_CONTEXT


def priority_label_for(
    artifacts: SignalPriorityArtifacts,
    final_score: Decimal,
    review_bucket: SignalReviewBucket,
    settings: Settings,
) -> SignalPriorityLabel:
    if review_bucket == SignalReviewBucket.STALE_OR_DATA_ISSUE:
        return SignalPriorityLabel.STALE
    if review_bucket == SignalReviewBucket.AVOID_OR_NO_DIRECTIONAL_SIGNAL:
        return SignalPriorityLabel.AVOID
    if (
        review_bucket == SignalReviewBucket.REVIEW_REQUIRED
        and final_score >= settings.signal_priority_review_required_threshold
    ):
        return SignalPriorityLabel.URGENT_REVIEW
    if has_critical_artifact_issue(artifacts):
        return SignalPriorityLabel.URGENT_REVIEW
    if final_score >= settings.signal_priority_high_threshold:
        return SignalPriorityLabel.HIGH
    if final_score >= settings.signal_priority_medium_threshold:
        return SignalPriorityLabel.MEDIUM
    return SignalPriorityLabel.LOW


def missing_component(reason: str, source_artifact: str) -> ComponentScore:
    return ComponentScore(
        score=Decimal("0.5000"),
        reason=reason,
        source_artifact=source_artifact,
        missing=True,
    )


def cross_asset_result_score(result: CrossAssetContextResult) -> Decimal:
    label_score = {
        "aligned": Decimal("0.8500"),
        "partially_aligned": Decimal("0.6500"),
        "conflicting": Decimal("0.2500"),
        "divergent": Decimal("0.3000"),
        "insufficient_data": Decimal("0.4000"),
    }.get(result.alignment_label, Decimal("0.5000"))
    quality_multiplier = {
        "strong": Decimal("1.0000"),
        "acceptable": Decimal("0.9000"),
        "degraded": Decimal("0.7000"),
        "insufficient_data": Decimal("0.5000"),
    }.get(result.data_quality_label, Decimal("0.8000"))
    return clamp(label_score * quality_multiplier)


def historical_search_score(results_json: list[dict[str, object]]) -> Decimal:
    if not results_json:
        return Decimal("0.5500")
    scores: list[Decimal] = []
    for result in results_json[:10]:
        similarity = decimal_from_any(
            result.get("similarityScore")
            or result.get("similarity_score")
            or result.get("score")
            or Decimal("0.5500")
        )
        outcome = result.get("outcomeSummary") or result.get("outcome_summary")
        if isinstance(outcome, dict):
            scores.append((similarity + outcome_summary_score(outcome)) / Decimal("2"))
        else:
            scores.append(similarity)
    return decimal_score(sum(scores, ZERO) / Decimal(len(scores)))


def outcome_summary_score(summary: dict[str, object]) -> Decimal:
    text = str(summary).lower()
    if "continuation" in text or "partial_follow_through" in text:
        return Decimal("0.7000")
    if "reversal" in text or "no_follow_through" in text:
        return Decimal("0.3500")
    if "insufficient" in text or "failed" in text:
        return Decimal("0.4000")
    return Decimal("0.5500")


def outcomes_score(outcomes: list[SignalOutcome]) -> Decimal:
    if not outcomes:
        return Decimal("0.5500")
    values = [
        {
            "continuation": Decimal("0.7500"),
            "partial_follow_through": Decimal("0.6500"),
            "sideways_after_signal": Decimal("0.5000"),
            "no_follow_through": Decimal("0.3500"),
            "reversal": Decimal("0.2500"),
            "insufficient_data": Decimal("0.4000"),
            "not_directional": Decimal("0.4000"),
            "failed": Decimal("0.3000"),
        }.get(outcome.outcome_label, Decimal("0.5000"))
        for outcome in outcomes
    ]
    return decimal_score(sum(values, ZERO) / Decimal(len(values)))


def cohort_drift_score(results: list[CohortDriftResult]) -> Decimal:
    if not results:
        return Decimal("0.5500")
    worst = max(results, key=lambda result: Decimal(result.drift_score))
    return {
        "no_drift": Decimal("0.8000"),
        "mild_drift": Decimal("0.6500"),
        "moderate_drift": Decimal("0.4500"),
        "severe_drift": Decimal("0.2000"),
        "low_sample": Decimal("0.5000"),
        "insufficient_data": Decimal("0.4000"),
    }.get(worst.drift_label, Decimal("0.5000"))


def has_stale_data(artifacts: SignalPriorityArtifacts) -> bool:
    memory = artifacts.market_memory
    if memory is not None and memory.freshness_label in {"stale", "no_data"}:
        return True
    if artifacts.setup_context is not None:
        return any(
            str(warning.get("code") or "").lower() == "data_stale"
            for warning in artifacts.setup_context.data_quality_warnings_json
        )
    return False


def has_low_data_quality(artifacts: SignalPriorityArtifacts) -> bool:
    if artifacts.data_quality_run is not None:
        return artifacts.data_quality_run.quality_label in {
            "degraded",
            "poor",
            "insufficient_data",
        }
    memory = artifacts.market_memory
    if memory is not None:
        return memory.data_quality_label in {"degraded", "poor", "insufficient"}
    return False


def has_conflicting_evidence(artifacts: SignalPriorityArtifacts) -> bool:
    signal = artifacts.signal
    return (
        any(evidence_conflicts_with_signal(item, signal) for item in artifacts.evidence)
        or has_timeframe_conflict(artifacts.multi_timeframe_context, artifacts.setup_context)
        or any(
            result.alignment_label in {"conflicting", "divergent"}
            for result in artifacts.cross_asset_results
        )
        or any(
            finding.finding_type in {"contradiction", "shadow_disagreement"}
            for finding in artifacts.intelligence_quality_findings
        )
        or has_shadow_disagreement(artifacts.shadow_classifications)
    )


def is_not_directional(signal: Signal) -> bool:
    return (
        signal.classification_status != "signal"
        or signal.bias in {"neutral", "unclear"}
        or (signal.no_signal_reason is not None and signal.no_signal_reason != "")
    )


def has_blocked_readiness(readiness: DecisionReadinessAssessment | None) -> bool:
    return readiness is not None and readiness.readiness_label == "blocked"


def has_failed_quality_safety(artifacts: SignalPriorityArtifacts) -> bool:
    return any(
        finding.finding_type in {"grounding_issue", "safety_issue"}
        and finding.severity in {"high", "critical"}
        for finding in artifacts.intelligence_quality_findings
    )


def has_pending_data_recovery(artifacts: SignalPriorityArtifacts) -> bool:
    if any(item.action_type == "wait_for_more_final_candles" for item in artifacts.action_items):
        return True
    memory = artifacts.market_memory
    if memory is not None:
        text = str(memory.warnings_json).lower()
        return "gap" in text or "missing" in text or "recovery" in text
    return False


def has_pending_human_review(action_items: list[ReasoningActionItem]) -> bool:
    return any(item.action_type == "request_human_review" for item in action_items)


def has_recent_follow_through(outcomes: list[SignalOutcome]) -> bool:
    return any(
        outcome.outcome_label in {"continuation", "partial_follow_through"} for outcome in outcomes
    )


def has_review_required(artifacts: SignalPriorityArtifacts, final_score: Decimal) -> bool:
    return (
        has_blocked_readiness(artifacts.decision_readiness)
        or has_failed_quality_safety(artifacts)
        or has_severity(artifacts.intelligence_quality_findings, "critical")
        or any(note.severity == "critical" for note in artifacts.risk_notes)
        or final_score >= Decimal("0.9000")
    )


def has_critical_artifact_issue(artifacts: SignalPriorityArtifacts) -> bool:
    return (
        has_blocked_readiness(artifacts.decision_readiness)
        or any(note.severity == "critical" for note in artifacts.risk_notes)
        or has_severity(artifacts.intelligence_quality_findings, "critical")
    )


def has_avoid_condition(setup_context: SetupContext | None) -> bool:
    if setup_context is None:
        return False
    return setup_context.setup_quality_label == "avoid_condition" or bool(
        setup_context.avoid_reasons_json
    )


def needs_confirmation(
    artifacts: SignalPriorityArtifacts,
    components: dict[str, ComponentScore],
) -> bool:
    return (
        components["confidence_component"].score < Decimal("0.7500")
        or components["setup_quality_component"].score < Decimal("0.7500")
        or components["timeframe_agreement_component"].missing
        or not artifacts.outcomes
        or bool(artifacts.action_items)
        or bool(artifacts.setup_context and artifacts.setup_context.wait_conditions_json)
    )


def evidence_conflicts_with_signal(evidence: SignalEvidence, signal: Signal) -> bool:
    direction = evidence.direction.lower()
    if "conflict" in direction:
        return True
    if signal.bias == "bullish":
        return "bearish" in direction
    if signal.bias == "bearish":
        return "bullish" in direction
    return False


def has_timeframe_conflict(
    context: MultiTimeframeContext | None,
    setup_context: SetupContext | None,
) -> bool:
    if context is not None:
        return context.agreement_label == "conflicting"
    if setup_context is not None:
        text = str(setup_context.timeframe_agreement_json).lower()
        return "conflicting" in text or "conflict" in text
    return False


def has_shadow_disagreement(results: list[ShadowClassificationResult]) -> bool:
    return any(
        result.agreement_with_final not in {"agreed", "not_applicable"} for result in results
    )


def has_severity(findings: list[IntelligenceQualityFinding], severity: str) -> bool:
    threshold = SEVERITY_ORDER[severity]
    return any(SEVERITY_ORDER.get(finding.severity, 0) >= threshold for finding in findings)


def penalty(
    code: str,
    amount: Decimal,
    reason: str,
    source: str = "signal_priority",
    **metadata: object,
) -> dict[str, object]:
    return {
        "code": code,
        "amount": decimal_score(amount),
        "reason": reason,
        "source": source,
        **metadata,
    }


def booster(code: str, amount: Decimal, reason: str) -> dict[str, object]:
    return {
        "code": code,
        "amount": decimal_score(amount),
        "reason": reason,
        "source": "signal_priority",
    }


def sum_decimal_values(items: list[dict[str, object]]) -> Decimal:
    return sum((decimal_from_any(item.get("amount", ZERO)) for item in items), ZERO)


def decimal_from_any(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int | float | str):
        return Decimal(str(value))
    return ZERO


def decimal_score(value: Decimal) -> Decimal:
    return clamp(value).quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def clamp(value: Decimal) -> Decimal:
    return min(ONE, max(ZERO, value))


def safe_text(value: str) -> str:
    return value.replace("buy", "review").replace("sell", "review")


def to_json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(decimal_score(value))
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        resolved = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return resolved.isoformat()
    if isinstance(value, list):
        return [to_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_json_value(nested_value) for key, nested_value in value.items()}
    return value
