from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.modules.analysis.models import AnalysisMode
from app.modules.explanations.safety import check_explanation_safety
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFindingType,
    IntelligenceQualityLabel,
    IntelligenceQualitySeverity,
)
from app.modules.intelligence_quality.repository import IntelligenceQualityArtifacts
from app.modules.news.models import CorrelationLabel
from app.modules.patterns.models import PatternCandidate
from app.modules.signals.confidence import confidence_label
from app.modules.signals.models import Signal

QUALITY_GATE_VERSION = "quality_gates_v1"
SCORE_PENALTIES: dict[str, Decimal] = {
    IntelligenceQualitySeverity.INFO.value: Decimal("0.0100"),
    IntelligenceQualitySeverity.LOW.value: Decimal("0.0300"),
    IntelligenceQualitySeverity.MEDIUM.value: Decimal("0.0800"),
    IntelligenceQualitySeverity.HIGH.value: Decimal("0.1800"),
    IntelligenceQualitySeverity.CRITICAL.value: Decimal("0.3500"),
}
TOLERANCE = Decimal("0.0100")
WEIGHT_TOLERANCE = Decimal("0.0500")
SUPPORTED_SAFE_ACTIONS = {
    "evaluate_outcome_after_horizon",
    "replay_analysis",
    "run_news_correlation",
    "wait_for_final_candles",
    "human_review",
    "no_action",
}
UNSAFE_DIRECTIVE_TERMS = (
    "buy",
    "sell",
    "enter",
    "exit",
    "leverage",
    "order",
    "guarantee",
    "guaranteed",
    "risk-free",
    "sure win",
    "cannot lose",
)
CAUSATION_TERMS = (
    "caused",
    "causes",
    "because of the news",
    "confirmed by news",
    "news drove",
    "definitely caused",
)
CAUTIOUS_TERMS = ("possible", "may", "might", "could", "context", "correlation")
DIRECTIONAL_OUTCOME_LABELS = {
    "continuation",
    "partial_follow_through",
    "no_follow_through",
    "reversal",
}
NON_DIRECTIONAL_OUTCOME_LABELS = {
    "not_directional",
    "sideways_after_signal",
    "insufficient_data",
    "failed",
}


@dataclass(frozen=True)
class FindingDraft:
    finding_type: str
    severity: str
    code: str
    title: str
    message: str
    artifact_type: str
    artifact_id: UUID | None = None
    expected_value: str | None = None
    observed_value: str | None = None
    metadata_json: dict[str, object] | None = None


@dataclass(frozen=True)
class QualityScoreResult:
    quality_score: Decimal
    quality_label: str
    status: str
    summary: str


class IntelligenceQualityGateService:
    def run_gates(
        self,
        artifacts: IntelligenceQualityArtifacts,
        require_signal: bool,
    ) -> list[FindingDraft]:
        findings: list[FindingDraft] = []
        findings.extend(self.required_artifact_findings(artifacts, require_signal))
        findings.extend(self.signal_candidate_findings(artifacts))
        findings.extend(self.confidence_findings(artifacts))
        findings.extend(self.evidence_findings(artifacts))
        findings.extend(self.risk_confidence_findings(artifacts))
        findings.extend(self.explanation_findings(artifacts))
        findings.extend(self.llm_reasoning_findings(artifacts))
        findings.extend(self.outcome_findings(artifacts))
        findings.extend(self.news_findings(artifacts))
        findings.extend(self.replay_findings(artifacts))
        findings.extend(self.review_recommendation_findings(findings))
        return findings

    def required_artifact_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
        require_signal: bool,
    ) -> list[FindingDraft]:
        findings: list[FindingDraft] = []
        if artifacts.analysis_run is None:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.HIGH,
                    "missing_analysis_run",
                    "Analysis run missing",
                    "Required analysis run artifact was not found.",
                    "analysis_run",
                )
            )
        if require_signal and artifacts.signal is None:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.HIGH,
                    "missing_signal",
                    "Signal missing",
                    "Required signal artifact was not found.",
                    "signal",
                )
            )
        if artifacts.feature_snapshot is None:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "missing_feature_snapshot",
                    "Feature snapshot missing",
                    "Feature snapshot is required for predictable analysis validation.",
                    "feature_snapshot",
                    artifact_id=optional_analysis_run_id(artifacts),
                )
            )
        if artifacts.indicator_snapshot is None and not has_risk_code(
            artifacts,
            "missing_indicator_snapshot",
        ):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "missing_indicator_snapshot",
                    "Indicator snapshot missing",
                    "Indicator snapshot is missing without a persisted degraded-confidence note.",
                    "indicator_snapshot",
                    artifact_id=optional_analysis_run_id(artifacts),
                )
            )
        if not artifacts.pattern_candidates:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "missing_pattern_candidates",
                    "Pattern candidates missing",
                    "No persisted pattern candidates were available for validation.",
                    "pattern_candidate",
                    artifact_id=optional_analysis_run_id(artifacts),
                )
            )
        if artifacts.signal is not None and not artifacts.confidence_components:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "missing_confidence_components",
                    "Confidence components missing",
                    "Signal is missing persisted confidence components.",
                    "signal",
                    artifact_id=artifacts.signal.id,
                )
            )
        if artifacts.signal is not None and not artifacts.evidence:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "missing_signal_evidence",
                    "Signal evidence missing",
                    "Signal is missing persisted evidence rows.",
                    "signal",
                    artifact_id=artifacts.signal.id,
                )
            )
        if artifacts.signal is not None and artifacts.deterministic_explanation is None:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "missing_deterministic_explanation",
                    "Deterministic explanation missing",
                    "Signal is missing its deterministic explanation artifact.",
                    "signal",
                    artifact_id=artifacts.signal.id,
                )
            )
        return findings

    def signal_candidate_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        signal = artifacts.signal
        if signal is None:
            return []
        selected = selected_candidate(artifacts)
        findings: list[FindingDraft] = []
        if (
            signal.classification_status == "signal"
            and signal.selected_pattern_candidate_id is None
        ):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.HIGH,
                    "selected_candidate_missing",
                    "Selected candidate missing",
                    "Directional signal is missing a selected pattern candidate reference.",
                    "signal",
                    signal.id,
                )
            )
        if signal.selected_pattern_candidate_id is not None and selected is None:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.HIGH,
                    "selected_candidate_missing",
                    "Selected candidate not found",
                    "Signal references a selected pattern candidate that is not persisted.",
                    "pattern_candidate",
                    signal.selected_pattern_candidate_id,
                )
            )
            return findings
        if selected is None:
            return findings
        if signal.pattern_type != selected.pattern_type:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.HIGH,
                    "selected_candidate_pattern_mismatch",
                    "Selected candidate pattern mismatch",
                    "Signal pattern does not match the selected pattern candidate.",
                    "signal",
                    signal.id,
                    expected_value=selected.pattern_type,
                    observed_value=signal.pattern_type,
                )
            )
        if signal.bias in {"bullish", "bearish", "neutral"} and signal.bias != selected.bias:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.CONTRADICTION,
                    IntelligenceQualitySeverity.HIGH,
                    "selected_candidate_bias_mismatch",
                    "Selected candidate bias mismatch",
                    "Signal bias does not match the selected pattern candidate.",
                    "signal",
                    signal.id,
                    expected_value=selected.bias,
                    observed_value=signal.bias,
                )
            )
        if signal.candidate_strength is not None and abs(
            signal.candidate_strength - selected.strength_score
        ) > TOLERANCE:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.MEDIUM,
                    "candidate_strength_mismatch",
                    "Candidate strength mismatch",
                    "Signal candidate strength does not match the selected candidate.",
                    "signal",
                    signal.id,
                    expected_value=str(selected.strength_score),
                    observed_value=str(signal.candidate_strength),
                )
            )
        if not selected.is_selected:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.LOW,
                    "selected_candidate_not_marked_selected",
                    "Selected candidate flag mismatch",
                    "Signal references a candidate that is not marked selected.",
                    "pattern_candidate",
                    selected.id,
                )
            )
        return findings

    def confidence_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        signal = artifacts.signal
        if signal is None or not artifacts.confidence_components:
            return []
        findings: list[FindingDraft] = []
        weighted_total = Decimal("0")
        weight_total = Decimal("0")
        for component in artifacts.confidence_components:
            expected_weighted = (component.component_score * component.component_weight).quantize(
                Decimal("0.00001")
            )
            weighted_total += component.weighted_score
            weight_total += component.component_weight
            if abs(component.weighted_score - expected_weighted) > Decimal("0.00011"):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.INVARIANT_FAILURE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "confidence_component_weight_mismatch",
                        "Confidence component mismatch",
                        "A confidence component weighted score does not match score times weight.",
                        "confidence_component",
                        component.id,
                        expected_value=str(expected_weighted),
                        observed_value=str(component.weighted_score),
                    )
                )
        if abs(weight_total - Decimal("1.0000")) > WEIGHT_TOLERANCE:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.LOW,
                    "component_weights_not_normalized",
                    "Confidence weights not normalized",
                    "Confidence component weights do not sum near one.",
                    "signal",
                    signal.id,
                    expected_value="1.0000",
                    observed_value=str(weight_total),
                )
            )
        expected_total = weighted_total
        if weight_total > Decimal("0") and abs(weight_total - Decimal("1.0000")) > WEIGHT_TOLERANCE:
            expected_total = weighted_total / weight_total
        expected_total = clamp_decimal(expected_total)
        if abs(signal.confidence_score - expected_total) > TOLERANCE:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.HIGH,
                    "confidence_total_mismatch",
                    "Confidence total mismatch",
                    "Signal confidence does not match persisted confidence components.",
                    "signal",
                    signal.id,
                    expected_value=str(expected_total),
                    observed_value=str(signal.confidence_score),
                )
            )
        expected_label = confidence_label(signal.confidence_score).value
        if signal.confidence_label != expected_label:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.INVARIANT_FAILURE,
                    IntelligenceQualitySeverity.MEDIUM,
                    "confidence_label_mismatch",
                    "Confidence label mismatch",
                    "Signal confidence label does not match the persisted confidence score.",
                    "signal",
                    signal.id,
                    expected_value=expected_label,
                    observed_value=signal.confidence_label,
                )
            )
        data_quality = nested_decimal(
            artifacts.feature_snapshot.features_json if artifacts.feature_snapshot else None,
            "dataQuality",
            "qualityScore",
        )
        if data_quality is not None and data_quality < Decimal("0.7000"):
            has_low_quality_note = any(
                "quality" in note.code.lower() or "data" in note.code.lower()
                for note in artifacts.risk_notes
            )
            if signal.confidence_score >= Decimal("0.7000") and not has_low_quality_note:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.DEGRADED_CONFIDENCE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "low_data_quality_without_risk_note",
                        "Low data quality missing risk note",
                        "Low data quality is not reflected in confidence or risk notes.",
                        "signal",
                        signal.id,
                    )
                )
        return findings

    def evidence_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        signal = artifacts.signal
        if signal is None:
            return []
        findings: list[FindingDraft] = []
        bullish_weight = Decimal("0")
        bearish_weight = Decimal("0")
        for item in artifacts.evidence:
            direction = item.direction.lower()
            if item.weight < Decimal("0"):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.INVARIANT_FAILURE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "evidence_negative_weight",
                        "Evidence weight invalid",
                        "Signal evidence contains a negative weight.",
                        "signal_evidence",
                        item.id,
                    )
                )
            if contains_unsafe_language(item.message):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.SAFETY_ISSUE,
                        IntelligenceQualitySeverity.HIGH,
                        "unsafe_evidence_language",
                        "Evidence language requires review",
                        "Evidence contains non-permitted market directive language.",
                        "signal_evidence",
                        item.id,
                    )
                )
            if "bullish" in direction:
                bullish_weight += max(item.weight, Decimal("0"))
            if "bearish" in direction:
                bearish_weight += max(item.weight, Decimal("0"))
        has_contradiction_note = any(
            "conflict" in note.code.lower()
            or "risk" in note.code.lower()
            or "contradict" in note.message.lower()
            for note in artifacts.risk_notes
        )
        if (
            signal.bias == "bullish"
            and bearish_weight > bullish_weight
            and not has_contradiction_note
        ):
            findings.append(evidence_conflict_finding(signal, "bearish", "bullish"))
        if (
            signal.bias == "bearish"
            and bullish_weight > bearish_weight
            and not has_contradiction_note
        ):
            findings.append(evidence_conflict_finding(signal, "bullish", "bearish"))
        if signal.bias in {"neutral", "unclear"} and (
            bullish_weight > Decimal("0") or bearish_weight > Decimal("0")
        ):
            has_explanation = artifacts.deterministic_explanation is not None
            if not has_explanation:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.CONTRADICTION,
                        IntelligenceQualitySeverity.LOW,
                        "neutral_signal_directional_evidence_without_explanation",
                        "Directional evidence needs context",
                        "Neutral or unclear signal has directional evidence without explanation.",
                        "signal",
                        signal.id,
                    )
                )
        return findings

    def risk_confidence_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        signal = artifacts.signal
        if signal is None:
            return []
        findings: list[FindingDraft] = []
        high_risk = [
            note for note in artifacts.risk_notes if note.severity in {"high", "critical"}
        ]
        if signal.confidence_label == "very_high" and high_risk:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.CONTRADICTION,
                    IntelligenceQualitySeverity.HIGH,
                    "high_confidence_with_high_risk",
                    "High confidence with severe risk",
                    "Very high confidence appears together with severe risk notes.",
                    "signal",
                    signal.id,
                )
            )
        summary = signal.summary.lower()
        if signal.no_signal_reason in {"fakeout_risk", "chop_or_sideways_market"} and any(
            phrase in summary for phrase in ("clean breakout", "clear breakout", "strong breakout")
        ):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.CONTRADICTION,
                    IntelligenceQualitySeverity.MEDIUM,
                    "no_signal_reason_summary_conflict",
                    "No-signal summary conflict",
                    "No-signal reason conflicts with the persisted summary language.",
                    "signal",
                    signal.id,
                )
            )
        low_quality_note = any("quality" in note.code.lower() for note in artifacts.risk_notes)
        if low_quality_note and signal.confidence_score >= Decimal("0.8500"):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.CONTRADICTION,
                    IntelligenceQualitySeverity.MEDIUM,
                    "data_quality_confidence_conflict",
                    "Data quality confidence conflict",
                    "Low data quality risk is paired with very high confidence.",
                    "signal",
                    signal.id,
                )
            )
        return findings

    def explanation_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        signal = artifacts.signal
        explanation = artifacts.deterministic_explanation
        if signal is None or explanation is None:
            return []
        findings: list[FindingDraft] = []
        text = explanation.full_text.lower()
        if signal.bias in {"bullish", "bearish"}:
            opposite = "bearish" if signal.bias == "bullish" else "bullish"
            if opposite in text and signal.bias not in text:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.CONTRADICTION,
                        IntelligenceQualitySeverity.MEDIUM,
                        "deterministic_explanation_signal_mismatch",
                        "Deterministic explanation mismatch",
                        "Deterministic explanation does not align with persisted signal bias.",
                        "deterministic_explanation",
                        explanation.id,
                    )
                )
        if (
            signal.pattern_type is not None
            and "pattern" in text
            and signal.pattern_type not in text
        ):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.CONTRADICTION,
                    IntelligenceQualitySeverity.LOW,
                    "deterministic_explanation_signal_mismatch",
                    "Deterministic explanation pattern mismatch",
                    "Deterministic explanation references pattern context without "
                    "matching the signal.",
                    "deterministic_explanation",
                    explanation.id,
                )
            )
        if not check_explanation_safety(explanation.full_text).passed:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.SAFETY_ISSUE,
                    IntelligenceQualitySeverity.HIGH,
                    "unsafe_explanation_language",
                    "Explanation language requires review",
                    "Deterministic explanation contains non-permitted market directive language.",
                    "deterministic_explanation",
                    explanation.id,
                )
            )
        if "news" in text and not artifacts.news_correlations:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.GROUNDING_ISSUE,
                    IntelligenceQualitySeverity.MEDIUM,
                    "ungrounded_news_mention",
                    "Ungrounded news mention",
                    "Deterministic explanation mentions news without persisted correlation.",
                    "deterministic_explanation",
                    explanation.id,
                )
            )
        if contains_causation_language(explanation.full_text):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.SAFETY_ISSUE,
                    IntelligenceQualitySeverity.MEDIUM,
                    "causation_language_detected",
                    "Causation language detected",
                    "Explanation uses causation language that should remain cautious.",
                    "deterministic_explanation",
                    explanation.id,
                )
            )
        if signal.classification_status != "signal" and signal.no_signal_reason is not None:
            reason = signal.no_signal_reason.replace("_", " ")
            no_signal_text = (explanation.no_signal_summary or explanation.full_text).lower()
            if reason not in no_signal_text:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.CONTRADICTION,
                        IntelligenceQualitySeverity.LOW,
                        "no_signal_explanation_reason_mismatch",
                        "No-signal explanation mismatch",
                        "No-signal explanation does not reflect the persisted no-signal reason.",
                        "deterministic_explanation",
                        explanation.id,
                        expected_value=signal.no_signal_reason,
                    )
                )
        return findings

    def llm_reasoning_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        findings: list[FindingDraft] = []
        llm = artifacts.llm_explanation
        if llm is not None:
            if llm.safety_status == "blocked" and llm.output_text:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.SAFETY_ISSUE,
                        IntelligenceQualitySeverity.HIGH,
                        "exposed_blocked_llm_output",
                        "Blocked LLM output exposed",
                        "Blocked LLM explanation has exposed output text.",
                        "llm_explanation",
                        llm.id,
                    )
                )
            if llm.grounding_status == "failed" and llm.output_text:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.GROUNDING_ISSUE,
                        IntelligenceQualitySeverity.HIGH,
                        "failed_grounding_exposed",
                        "Failed grounding output exposed",
                        "LLM explanation with failed grounding has exposed output text.",
                        "llm_explanation",
                        llm.id,
                    )
                )
        signal = artifacts.signal
        for run in artifacts.reasoning_runs:
            if run.safety_status == "blocked" and (run.output_text or run.output_json):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.SAFETY_ISSUE,
                        IntelligenceQualitySeverity.HIGH,
                        "exposed_blocked_llm_output",
                        "Blocked reasoning output exposed",
                        "Blocked reasoning run has exposed output content.",
                        "reasoning_run",
                        run.id,
                    )
                )
            if run.grounding_status == "failed" and (run.output_text or run.output_json):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.GROUNDING_ISSUE,
                        IntelligenceQualitySeverity.HIGH,
                        "failed_grounding_exposed",
                        "Failed grounding reasoning exposed",
                        "Reasoning run with failed grounding has exposed output content.",
                        "reasoning_run",
                        run.id,
                    )
                )
            if signal is not None and run.signal_id not in {None, signal.id}:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.GROUNDING_ISSUE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "reasoning_artifact_mismatch",
                        "Reasoning artifact mismatch",
                        "Reasoning run does not match the validated signal.",
                        "reasoning_run",
                        run.id,
                        expected_value=str(signal.id),
                        observed_value=str(run.signal_id),
                    )
                )
        for scenario in artifacts.scenario_hypotheses:
            rejected_actions = [
                action
                for action in scenario.suggested_backend_actions_json
                if action not in SUPPORTED_SAFE_ACTIONS or contains_unsafe_language(action)
            ]
            if rejected_actions:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.SAFETY_ISSUE,
                        IntelligenceQualitySeverity.HIGH,
                        "unsafe_scenario_action",
                        "Scenario action requires review",
                        "Scenario contains a non-permitted backend action.",
                        "scenario_hypothesis",
                        scenario.id,
                    )
                )
        return findings

    def outcome_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        signal = artifacts.signal
        if signal is None:
            return []
        findings: list[FindingDraft] = []
        for outcome in artifacts.outcomes:
            if outcome.signal_id != signal.id:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.INVARIANT_FAILURE,
                        IntelligenceQualitySeverity.HIGH,
                        "outcome_signal_mismatch",
                        "Outcome signal mismatch",
                        "Outcome row does not reference the validated signal.",
                        "signal_outcome",
                        outcome.id,
                        expected_value=str(signal.id),
                        observed_value=str(outcome.signal_id),
                    )
                )
            if outcome.bias != signal.bias:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.CONTRADICTION,
                        IntelligenceQualitySeverity.HIGH,
                        "outcome_bias_mismatch",
                        "Outcome bias mismatch",
                        "Outcome bias snapshot does not match the persisted signal.",
                        "signal_outcome",
                        outcome.id,
                        expected_value=signal.bias,
                        observed_value=outcome.bias,
                    )
                )
            if signal.classification_status != "signal" and outcome.outcome_label not in (
                NON_DIRECTIONAL_OUTCOME_LABELS
            ):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.CONTRADICTION,
                        IntelligenceQualitySeverity.MEDIUM,
                        "non_directional_outcome_label_conflict",
                        "Non-directional outcome label conflict",
                        "Non-directional signal has a directional outcome label.",
                        "signal_outcome",
                        outcome.id,
                    )
                )
            if (
                signal.classification_status == "signal"
                and outcome.outcome_label in DIRECTIONAL_OUTCOME_LABELS
                and outcome.future_candle_count > 0
                and outcome.max_favorable_move == Decimal("0")
                and outcome.max_adverse_move == Decimal("0")
                and outcome.net_move == Decimal("0")
            ):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.MISSING_ARTIFACT,
                        IntelligenceQualitySeverity.MEDIUM,
                        "missing_directional_outcome_metrics",
                        "Directional outcome metrics missing",
                        "Directional outcome label is missing movement metrics.",
                        "signal_outcome",
                        outcome.id,
                    )
                )
            missing_symbol_size = outcome.metadata_json.get("missingSymbolSize") is True
            has_conversions = any(
                value is not None
                for value in (
                    outcome.max_favorable_pips,
                    outcome.max_adverse_pips,
                    outcome.net_pips,
                    outcome.max_favorable_ticks,
                    outcome.max_adverse_ticks,
                    outcome.net_ticks,
                )
            )
            if missing_symbol_size and has_conversions:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.INVARIANT_FAILURE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "invalid_pip_tick_conversion",
                        "Invalid pip or tick conversion",
                        "Outcome has conversion metrics while symbol size metadata is missing.",
                        "signal_outcome",
                        outcome.id,
                    )
                )
        return findings

    def news_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        findings: list[FindingDraft] = []
        for correlation in artifacts.news_correlations:
            expected_label = correlation_label(correlation.correlation_score)
            if correlation.correlation_label != expected_label:
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.INVARIANT_FAILURE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "news_correlation_label_mismatch",
                        "News correlation label mismatch",
                        "News correlation label does not match the persisted score.",
                        "news_correlation",
                        correlation.id,
                        expected_value=expected_label,
                        observed_value=correlation.correlation_label,
                    )
                )
            reason = correlation.reason.lower()
            if correlation.correlation_label != CorrelationLabel.NONE.value and not any(
                term in reason for term in CAUTIOUS_TERMS
            ):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.GROUNDING_ISSUE,
                        IntelligenceQualitySeverity.LOW,
                        "news_correlation_caution_language_missing",
                        "News correlation caution missing",
                        "News correlation reason should use cautious contextual language.",
                        "news_correlation",
                        correlation.id,
                    )
                )
            if contains_causation_language(correlation.reason):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.SAFETY_ISSUE,
                        IntelligenceQualitySeverity.MEDIUM,
                        "news_correlation_causation_language",
                        "News causation language detected",
                        "News correlation reason uses causation language instead of "
                        "cautious context.",
                        "news_correlation",
                        correlation.id,
                    )
                )
            if abs(correlation.time_delta_minutes) > Decimal("10080"):
                findings.append(
                    finding(
                        IntelligenceQualityFindingType.INVARIANT_FAILURE,
                        IntelligenceQualitySeverity.LOW,
                        "news_correlation_time_delta_invalid",
                        "News correlation time delta unusual",
                        "News correlation time delta is outside the expected validation window.",
                        "news_correlation",
                        correlation.id,
                    )
                )
        return findings

    def replay_findings(
        self,
        artifacts: IntelligenceQualityArtifacts,
    ) -> list[FindingDraft]:
        run = artifacts.analysis_run
        if run is None or run.analysis_mode != AnalysisMode.REPLAY.value:
            return []
        findings: list[FindingDraft] = []
        if run.replayed_from_analysis_run_id is None:
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.HIGH,
                    "replay_link_missing",
                    "Replay link missing",
                    "Replay analysis run is missing its original analysis link.",
                    "analysis_run",
                    run.id,
                )
            )
        if run.replay_mode == "same_engine_version" and (
            run.engine_snapshot_json is None or run.rule_set_snapshot_json is None
        ):
            findings.append(
                finding(
                    IntelligenceQualityFindingType.MISSING_ARTIFACT,
                    IntelligenceQualitySeverity.MEDIUM,
                    "replay_engine_snapshot_missing",
                    "Replay engine snapshot missing",
                    "Same-engine replay is missing engine or rule-set snapshot metadata.",
                    "analysis_run",
                    run.id,
                )
            )
        return findings

    def review_recommendation_findings(
        self,
        findings: list[FindingDraft],
    ) -> list[FindingDraft]:
        recommendations: list[FindingDraft] = []
        existing_codes = {item.code for item in findings}
        recommendation_map = {
            "high_confidence_with_high_risk": (
                "review_high_confidence_with_high_risk",
                "Review recommended for confidence and risk",
                "Review this signal because high confidence appears with severe risk notes.",
            ),
            "ungrounded_news_mention": (
                "review_ungrounded_news_context",
                "Review recommended for news context",
                "Review this analysis because explanation mentions news without "
                "persisted correlation.",
            ),
            "non_directional_outcome_label_conflict": (
                "review_non_directional_outcome",
                "Review recommended for outcome label",
                "Review this outcome because a non-directional signal has a directional "
                "outcome label.",
            ),
            "failed_grounding_exposed": (
                "review_failed_grounding_output",
                "Review recommended for grounding",
                "Review this output because failed grounding content is exposed.",
            ),
        }
        for source_code, (code, title, message) in recommendation_map.items():
            if source_code in existing_codes:
                recommendations.append(
                    finding(
                        IntelligenceQualityFindingType.REVIEW_RECOMMENDATION,
                        IntelligenceQualitySeverity.MEDIUM,
                        code,
                        title,
                        message,
                        "quality_run",
                    )
                )
        return recommendations


def score_findings(findings: list[FindingDraft]) -> QualityScoreResult:
    score = Decimal("1.0000")
    for item in findings:
        score -= SCORE_PENALTIES[item.severity]
    score = clamp_decimal(score)
    label = label_for_score(score)
    if any_required_artifact_missing(findings) and label in {
        IntelligenceQualityLabel.STRONG.value,
        IntelligenceQualityLabel.ACCEPTABLE.value,
    }:
        label = IntelligenceQualityLabel.REVIEW_RECOMMENDED.value
    if any(
        item.severity == IntelligenceQualitySeverity.CRITICAL.value
        for item in findings
        if item.finding_type != IntelligenceQualityFindingType.REVIEW_RECOMMENDATION.value
    ):
        label = IntelligenceQualityLabel.INSUFFICIENT_CONTEXT.value
    status = "completed"
    if any(item.severity in {"medium", "high", "critical"} for item in findings):
        status = "completed_with_warnings"
    summary = f"{len(findings)} quality findings generated; label is {label}."
    return QualityScoreResult(
        quality_score=score,
        quality_label=label,
        status=status,
        summary=summary,
    )


def finding(
    finding_type: IntelligenceQualityFindingType,
    severity: IntelligenceQualitySeverity,
    code: str,
    title: str,
    message: str,
    artifact_type: str,
    artifact_id: UUID | None = None,
    expected_value: object | None = None,
    observed_value: object | None = None,
    metadata_json: dict[str, object] | None = None,
) -> FindingDraft:
    return FindingDraft(
        finding_type=finding_type.value,
        severity=severity.value,
        code=code,
        title=title,
        message=message,
        artifact_type=artifact_type,
        artifact_id=artifact_id,
        expected_value=str(expected_value) if expected_value is not None else None,
        observed_value=str(observed_value) if observed_value is not None else None,
        metadata_json=metadata_json or {},
    )


def with_quality_run_artifact(
    finding_draft: FindingDraft,
    artifact_id: UUID,
) -> FindingDraft:
    if finding_draft.artifact_type != "quality_run" or finding_draft.artifact_id is not None:
        return finding_draft
    return replace(finding_draft, artifact_id=artifact_id)


def selected_candidate(artifacts: IntelligenceQualityArtifacts) -> PatternCandidate | None:
    signal = artifacts.signal
    if signal is None or signal.selected_pattern_candidate_id is None:
        return None
    for candidate in artifacts.pattern_candidates:
        if candidate.id == signal.selected_pattern_candidate_id:
            return candidate
    return None


def optional_analysis_run_id(artifacts: IntelligenceQualityArtifacts) -> UUID | None:
    return artifacts.analysis_run.id if artifacts.analysis_run is not None else None


def has_risk_code(artifacts: IntelligenceQualityArtifacts, code: str) -> bool:
    return any(note.code == code for note in artifacts.risk_notes)


def nested_decimal(
    values: dict[str, object] | None,
    section: str,
    key: str,
) -> Decimal | None:
    if values is None:
        return None
    section_value = values.get(section)
    if not isinstance(section_value, dict):
        return None
    raw_value = section_value.get(key)
    if raw_value is None or isinstance(raw_value, bool):
        return None
    try:
        return Decimal(str(raw_value))
    except InvalidOperation:
        return None


def clamp_decimal(value: Decimal) -> Decimal:
    if value < Decimal("0"):
        return Decimal("0.0000")
    if value > Decimal("1"):
        return Decimal("1.0000")
    return value.quantize(Decimal("0.0001"))


def label_for_score(score: Decimal) -> str:
    if score >= Decimal("0.9000"):
        return IntelligenceQualityLabel.STRONG.value
    if score >= Decimal("0.7500"):
        return IntelligenceQualityLabel.ACCEPTABLE.value
    if score >= Decimal("0.5000"):
        return IntelligenceQualityLabel.REVIEW_RECOMMENDED.value
    if score >= Decimal("0.2000"):
        return IntelligenceQualityLabel.INCONSISTENT.value
    return IntelligenceQualityLabel.INSUFFICIENT_CONTEXT.value


def any_required_artifact_missing(findings: list[FindingDraft]) -> bool:
    required_codes = {
        "missing_analysis_run",
        "missing_signal",
        "missing_feature_snapshot",
        "missing_pattern_candidates",
        "missing_confidence_components",
        "missing_signal_evidence",
        "missing_deterministic_explanation",
    }
    return any(item.code in required_codes for item in findings)


def contains_unsafe_language(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(term in normalized for term in UNSAFE_DIRECTIVE_TERMS)


def contains_causation_language(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return any(term in normalized for term in CAUSATION_TERMS)


def evidence_conflict_finding(signal: Signal, observed: str, expected: str) -> FindingDraft:
    return finding(
        IntelligenceQualityFindingType.CONTRADICTION,
        IntelligenceQualitySeverity.MEDIUM,
        "evidence_direction_conflict",
        "Evidence direction conflict",
        "Majority evidence direction does not align with the final signal bias.",
        "signal",
        signal.id,
        expected_value=expected,
        observed_value=observed,
    )


def correlation_label(score: Decimal) -> str:
    if score < Decimal("0.2000"):
        return CorrelationLabel.NONE.value
    if score < Decimal("0.4500"):
        return CorrelationLabel.WEAK.value
    if score < Decimal("0.7500"):
        return CorrelationLabel.POSSIBLE.value
    return CorrelationLabel.STRONG.value
