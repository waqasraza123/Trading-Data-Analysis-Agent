import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from app.modules.explanation_comparison.models import (
    ExplanationAlignmentLabel,
    ExplanationComparisonFindingType,
    ExplanationComparisonSeverity,
)
from app.modules.explanation_comparison.repository import ExplanationComparisonArtifacts
from app.modules.reasoning.models import ReasoningGroundingStatus, ReasoningSafetyStatus
from app.modules.signals.models import SignalBias

NUMERIC_PATTERN = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")
WORD_PATTERN = re.compile(r"[a-z0-9]+")
UNSAFE_PHRASES = (
    "buy now",
    "sell now",
    "enter now",
    "exit now",
    "take this trade",
    "use leverage",
    "place order",
    "execute trade",
    "go long",
    "go short",
    "long now",
    "short now",
    "guaranteed profit",
    "profit guaranteed",
    "risk-free",
    "cannot lose",
)
UNSAFE_PATTERNS = (
    r"\b(?:should|must|need to|please)\s+buy\b",
    r"\b(?:should|must|need to|please)\s+sell\b",
    r"\b(?:should|must|need to|please)\s+enter\b",
    r"\b(?:should|must|need to|please)\s+exit\b",
)
CAUSATION_PHRASES = (
    "caused the move",
    "caused this move",
    "caused by",
    "definitely caused",
    "confirmed reason",
    "definitely drove",
    "definitely triggered",
    "news drove",
    "because of the news",
    "confirmed by news",
)
NEWS_KEYWORDS = (
    "news",
    "event",
    "announcement",
    "headline",
    "calendar",
    "cpi",
    "fomc",
    "rate decision",
)
ALLOWED_BACKEND_ACTIONS = {
    "evaluate_outcome_after_horizon",
    "run_replay",
    "run_news_correlation",
    "wait_for_more_final_candles",
    "request_human_review",
    "no_action",
}
PATTERN_TERMS = {
    "bullish_breakout": ("bullish breakout",),
    "bearish_breakdown": ("bearish breakdown",),
    "bullish_continuation": ("bullish continuation",),
    "bearish_continuation": ("bearish continuation",),
    "bullish_reversal": ("bullish reversal",),
    "bearish_reversal": ("bearish reversal",),
    "sideways_range": ("sideways range", "range"),
    "low_volatility_chop": ("low volatility chop", "chop"),
    "unclear_structure": ("unclear structure",),
    "fakeout": ("fakeout",),
}
BIAS_TERMS = {
    SignalBias.BULLISH.value: ("bullish", "upside", "upward", "higher", "rally"),
    SignalBias.BEARISH.value: ("bearish", "downside", "downward", "lower", "selloff"),
    SignalBias.NEUTRAL.value: ("neutral", "sideways", "range"),
}
SEVERITY_PENALTIES = {
    ExplanationComparisonSeverity.INFO.value: Decimal("0.0200"),
    ExplanationComparisonSeverity.LOW.value: Decimal("0.0500"),
    ExplanationComparisonSeverity.MEDIUM.value: Decimal("0.1200"),
    ExplanationComparisonSeverity.HIGH.value: Decimal("0.2500"),
    ExplanationComparisonSeverity.CRITICAL.value: Decimal("0.4500"),
}
REVIEW_SEVERITIES = {
    ExplanationComparisonSeverity.HIGH.value,
    ExplanationComparisonSeverity.CRITICAL.value,
}


@dataclass(frozen=True)
class ComparisonFindingDraft:
    finding_type: str
    severity: str
    code: str
    message: str
    source_reference: str | None = None
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExplanationComparisonResult:
    alignment_score: Decimal
    alignment_label: str
    summary: str
    metadata_json: dict[str, object]
    findings: list[ComparisonFindingDraft]


class ExplanationComparator:
    def compare(
        self,
        artifacts: ExplanationComparisonArtifacts,
        alignment_threshold: Decimal,
        review_threshold: Decimal,
    ) -> ExplanationComparisonResult:
        findings: list[ComparisonFindingDraft] = []
        findings.extend(required_context_findings(artifacts))
        findings.extend(llm_findings(artifacts))
        findings.extend(reasoning_findings(artifacts))
        findings.extend(scenario_ensemble_findings(artifacts))
        score = score_findings(findings)
        label = alignment_label_for(
            score=score,
            findings=findings,
            artifacts=artifacts,
            alignment_threshold=alignment_threshold,
            review_threshold=review_threshold,
        )
        operator_review_recommended = (
            score < review_threshold
            or label in {
                ExplanationAlignmentLabel.CONFLICTING.value,
                ExplanationAlignmentLabel.INSUFFICIENT_CONTEXT.value,
            }
            or any(finding.severity in REVIEW_SEVERITIES for finding in findings)
        )
        metadata_json = comparison_metadata(
            artifacts=artifacts,
            findings=findings,
            alignment_threshold=alignment_threshold,
            review_threshold=review_threshold,
            operator_review_recommended=operator_review_recommended,
        )
        return ExplanationComparisonResult(
            alignment_score=score,
            alignment_label=label,
            summary=summary_for(label, score, findings, operator_review_recommended),
            metadata_json=metadata_json,
            findings=findings,
        )


def required_context_findings(
    artifacts: ExplanationComparisonArtifacts,
) -> list[ComparisonFindingDraft]:
    findings: list[ComparisonFindingDraft] = []
    if artifacts.signal is None:
        return [
            finding(
                ExplanationComparisonFindingType.MISSING_CONTEXT,
                ExplanationComparisonSeverity.CRITICAL,
                "missing_signal",
                "Signal artifact was not found for explanation comparison.",
                "signal",
            )
        ]
    if artifacts.deterministic_explanation is None:
        findings.append(
            finding(
                ExplanationComparisonFindingType.MISSING_CONTEXT,
                ExplanationComparisonSeverity.HIGH,
                "missing_deterministic_explanation",
                "Deterministic explanation is required as the comparison baseline.",
                source_reference_for("signal", artifacts.signal.id),
            )
        )
    if artifacts.llm_explanation is None:
        findings.append(
            finding(
                ExplanationComparisonFindingType.MISSING_CONTEXT,
                ExplanationComparisonSeverity.MEDIUM,
                "missing_llm_explanation",
                "No persisted LLM explanation is available to compare with the "
                "deterministic explanation.",
                source_reference_for("signal", artifacts.signal.id),
            )
        )
    if artifacts.reasoning_run is None:
        findings.append(
            finding(
                ExplanationComparisonFindingType.MISSING_CONTEXT,
                ExplanationComparisonSeverity.LOW,
                "missing_reasoning_run",
                "No persisted scenario reasoning run is available for scenario alignment checks.",
                source_reference_for("signal", artifacts.signal.id),
            )
        )
    return findings


def llm_findings(artifacts: ExplanationComparisonArtifacts) -> list[ComparisonFindingDraft]:
    signal = artifacts.signal
    llm = artifacts.llm_explanation
    if signal is None or llm is None:
        return []
    findings: list[ComparisonFindingDraft] = []
    source_reference = source_reference_for("llm_explanation", llm.id)
    text = normalize_text(llm.output_text)
    input_payload = llm.input_json
    findings.extend(
        status_findings(
            safety_status=llm.safety_status,
            grounding_status=llm.grounding_status,
            blocked_terms=llm.blocked_terms_json,
            grounding_issues=llm.grounding_issues_json,
            source_reference=source_reference,
        )
    )
    findings.extend(
        bias_mismatch_findings(
            signal_bias=signal.bias,
            output_text=text,
            input_payload=input_payload,
            source_reference=source_reference,
        )
    )
    findings.extend(
        pattern_mismatch_findings(
            expected_pattern=signal.pattern_type,
            output_text=text,
            input_payload=input_payload,
            source_reference=source_reference,
        )
    )
    findings.extend(news_findings(artifacts, text, source_reference))
    findings.extend(risk_omission_findings(artifacts, text, source_reference))
    findings.extend(unsafe_language_findings(text, source_reference))
    findings.extend(causation_findings(text, source_reference))
    findings.extend(unsupported_numeric_findings(artifacts, llm.output_text, source_reference))
    return findings


def reasoning_findings(artifacts: ExplanationComparisonArtifacts) -> list[ComparisonFindingDraft]:
    signal = artifacts.signal
    reasoning = artifacts.reasoning_run
    if signal is None or reasoning is None:
        return []
    source_reference = source_reference_for("reasoning_run", reasoning.id)
    text = normalize_text(
        " ".join(
            [
                reasoning.output_text or "",
                json_text(reasoning.output_json or {}),
                scenario_text(artifacts),
            ]
        )
    )
    findings: list[ComparisonFindingDraft] = []
    findings.extend(
        status_findings(
            safety_status=reasoning.safety_status,
            grounding_status=reasoning.grounding_status,
            blocked_terms=reasoning.blocked_terms_json,
            grounding_issues=reasoning.grounding_issues_json,
            source_reference=source_reference,
        )
    )
    findings.extend(news_findings(artifacts, text, source_reference))
    findings.extend(unsafe_language_findings(text, source_reference))
    findings.extend(causation_findings(text, source_reference))
    findings.extend(unsupported_numeric_findings(artifacts, text, source_reference))
    findings.extend(scenario_action_findings(artifacts, source_reference))
    findings.extend(scenario_signal_contradiction_findings(artifacts, source_reference))
    return findings


def scenario_ensemble_findings(
    artifacts: ExplanationComparisonArtifacts,
) -> list[ComparisonFindingDraft]:
    ensemble_run = artifacts.scenario_ensemble_run
    if ensemble_run is None:
        return []
    source_reference = source_reference_for("scenario_ensemble", ensemble_run.id)
    findings: list[ComparisonFindingDraft] = []
    if ensemble_run.consensus_label == "disagreement":
        findings.append(
            finding(
                ExplanationComparisonFindingType.EXPLANATION_MISMATCH,
                ExplanationComparisonSeverity.MEDIUM,
                "scenario_ensemble_disagreement",
                "Scenario ensemble consensus reports disagreement across persisted "
                "reasoning layers.",
                source_reference,
                {"consensusScore": str(ensemble_run.consensus_score)},
            )
        )
    elif ensemble_run.consensus_label == "insufficient_context":
        findings.append(
            finding(
                ExplanationComparisonFindingType.MISSING_CONTEXT,
                ExplanationComparisonSeverity.LOW,
                "scenario_ensemble_insufficient_context",
                "Scenario ensemble consensus has insufficient context for cross-layer comparison.",
                source_reference,
                {"consensusScore": str(ensemble_run.consensus_score)},
            )
        )
    if ensemble_run.safety_status not in {"passed", "not_checked"}:
        findings.append(
            finding(
                ExplanationComparisonFindingType.UNSAFE_LANGUAGE,
                ExplanationComparisonSeverity.MEDIUM,
                "scenario_ensemble_safety_issue",
                "Scenario ensemble includes provider output with non-passing safety status.",
                source_reference,
                {"safetyStatus": ensemble_run.safety_status},
            )
        )
    if ensemble_run.grounding_status not in {"grounded", "not_checked"}:
        findings.append(
            finding(
                ExplanationComparisonFindingType.UNSUPPORTED_CLAIM,
                ExplanationComparisonSeverity.MEDIUM,
                "scenario_ensemble_grounding_issue",
                "Scenario ensemble includes provider output with non-grounded status.",
                source_reference,
                {"groundingStatus": ensemble_run.grounding_status},
            )
        )
    return findings


def status_findings(
    safety_status: str,
    grounding_status: str,
    blocked_terms: list[str],
    grounding_issues: list[str],
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    findings: list[ComparisonFindingDraft] = []
    if safety_status not in {ReasoningSafetyStatus.PASSED.value, "passed"}:
        findings.append(
            finding(
                ExplanationComparisonFindingType.UNSAFE_LANGUAGE,
                ExplanationComparisonSeverity.HIGH,
                "persisted_output_safety_not_passed",
                "Persisted explanation or reasoning output did not pass safety checks.",
                source_reference,
                {"safetyStatus": safety_status, "blockedTerms": blocked_terms},
            )
        )
    if grounding_status not in {ReasoningGroundingStatus.GROUNDED.value, "grounded"}:
        findings.append(
            finding(
                ExplanationComparisonFindingType.UNSUPPORTED_CLAIM,
                ExplanationComparisonSeverity.MEDIUM,
                "persisted_output_grounding_not_grounded",
                "Persisted explanation or reasoning output is not fully grounded.",
                source_reference,
                {"groundingStatus": grounding_status, "groundingIssues": grounding_issues},
            )
        )
    return findings


def bias_mismatch_findings(
    signal_bias: str,
    output_text: str,
    input_payload: dict[str, object],
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    if signal_bias not in BIAS_TERMS:
        return []
    opposite_biases = {
        SignalBias.BULLISH.value: (SignalBias.BEARISH.value,),
        SignalBias.BEARISH.value: (SignalBias.BULLISH.value,),
        SignalBias.NEUTRAL.value: (SignalBias.BULLISH.value, SignalBias.BEARISH.value),
    }.get(signal_bias, ())
    findings: list[ComparisonFindingDraft] = []
    for opposite_bias in opposite_biases:
        if contains_any_term(output_text, BIAS_TERMS[opposite_bias]):
            findings.append(
                finding(
                    ExplanationComparisonFindingType.CONTRADICTION,
                    ExplanationComparisonSeverity.HIGH,
                    "llm_bias_mismatch",
                    "LLM explanation mentions a directional bias that conflicts with the "
                    "persisted signal bias.",
                    source_reference,
                    {"expectedBias": signal_bias, "observedBiasTerm": opposite_bias},
                )
            )
            break
    structured_bias = nested_string(input_payload, "bias")
    if structured_bias and structured_bias != signal_bias:
        findings.append(
            finding(
                ExplanationComparisonFindingType.EXPLANATION_MISMATCH,
                ExplanationComparisonSeverity.HIGH,
                "llm_input_bias_mismatch",
                "LLM explanation input snapshot bias differs from the persisted signal bias.",
                source_reference,
                {"expectedBias": signal_bias, "observedBias": structured_bias},
            )
        )
    return findings


def pattern_mismatch_findings(
    expected_pattern: str | None,
    output_text: str,
    input_payload: dict[str, object],
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    findings: list[ComparisonFindingDraft] = []
    structured_pattern = nested_string(input_payload, "pattern_type")
    if structured_pattern is None:
        structured_pattern = nested_string(input_payload, "patternType")
    if structured_pattern and expected_pattern and structured_pattern != expected_pattern:
        findings.append(
            finding(
                ExplanationComparisonFindingType.EXPLANATION_MISMATCH,
                ExplanationComparisonSeverity.HIGH,
                "llm_input_pattern_mismatch",
                "LLM explanation input snapshot pattern differs from the persisted signal pattern.",
                source_reference,
                {"expectedPattern": expected_pattern, "observedPattern": structured_pattern},
            )
        )
    mentioned_patterns = mentioned_pattern_keys(output_text)
    if expected_pattern is None:
        if mentioned_patterns:
            findings.append(
                finding(
                    ExplanationComparisonFindingType.EXPLANATION_MISMATCH,
                    ExplanationComparisonSeverity.MEDIUM,
                    "unsupported_pattern_mention",
                    "LLM explanation mentions a pattern while the persisted signal has no "
                    "pattern type.",
                    source_reference,
                    {"mentionedPatterns": sorted(mentioned_patterns)},
                )
            )
        return findings
    normalized_expected = expected_pattern.lower()
    conflicting_patterns = sorted(
        pattern for pattern in mentioned_patterns if pattern != normalized_expected
    )
    if conflicting_patterns:
        findings.append(
            finding(
                ExplanationComparisonFindingType.EXPLANATION_MISMATCH,
                ExplanationComparisonSeverity.HIGH,
                "llm_pattern_mismatch",
                "LLM explanation mentions a pattern that conflicts with the persisted signal "
                "pattern.",
                source_reference,
                {"expectedPattern": expected_pattern, "mentionedPatterns": conflicting_patterns},
            )
        )
    return findings


def news_findings(
    artifacts: ExplanationComparisonArtifacts,
    text: str,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    if not mentions_news(text):
        return []
    if not artifacts.news_correlations:
        return [
            finding(
                ExplanationComparisonFindingType.UNSUPPORTED_CLAIM,
                ExplanationComparisonSeverity.HIGH,
                "unsupported_news_mention",
                "Persisted explanation layer mentions news or events without persisted news "
                "correlation evidence.",
                source_reference,
            )
        ]
    descriptors = news_descriptors(artifacts)
    if descriptors and not any(descriptor in text for descriptor in descriptors):
        return [
            finding(
                ExplanationComparisonFindingType.UNSUPPORTED_CLAIM,
                ExplanationComparisonSeverity.LOW,
                "news_mention_without_known_descriptor",
                "Persisted explanation layer mentions news or events without matching a stored "
                "event descriptor.",
                source_reference,
                {"knownDescriptors": sorted(descriptors)[:10]},
            )
        ]
    return []


def risk_omission_findings(
    artifacts: ExplanationComparisonArtifacts,
    output_text: str,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    findings: list[ComparisonFindingDraft] = []
    for note in artifacts.risk_notes:
        if note.severity not in {
            ExplanationComparisonSeverity.MEDIUM.value,
            ExplanationComparisonSeverity.HIGH.value,
            ExplanationComparisonSeverity.CRITICAL.value,
        }:
            continue
        if text_mentions_risk_note(output_text, note.code, note.message):
            continue
        severity = (
            ExplanationComparisonSeverity.HIGH
            if note.severity == ExplanationComparisonSeverity.CRITICAL.value
            else ExplanationComparisonSeverity.MEDIUM
        )
        findings.append(
            finding(
                ExplanationComparisonFindingType.OMITTED_RISK,
                severity,
                "important_risk_note_omitted",
                "LLM explanation omits an important persisted risk note.",
                source_reference,
                {
                    "riskNoteId": str(note.id),
                    "riskCode": note.code,
                    "riskSeverity": note.severity,
                },
            )
        )
    return findings


def unsafe_language_findings(
    text: str,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    blocked_terms = [phrase for phrase in UNSAFE_PHRASES if phrase_in_text(text, phrase)]
    blocked_terms.extend(pattern for pattern in UNSAFE_PATTERNS if re.search(pattern, text))
    if not blocked_terms:
        return []
    return [
        finding(
            ExplanationComparisonFindingType.UNSAFE_LANGUAGE,
            ExplanationComparisonSeverity.HIGH,
            "unsafe_trading_language",
            "Persisted explanation layer contains unsafe trading instruction or guarantee "
            "language.",
            source_reference,
            {"blockedTerms": sorted(set(blocked_terms))},
        )
    ]


def causation_findings(
    text: str,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    observed = [phrase for phrase in CAUSATION_PHRASES if phrase in text]
    if not observed:
        return []
    return [
        finding(
            ExplanationComparisonFindingType.CAUSATION_LANGUAGE,
            ExplanationComparisonSeverity.HIGH,
            "causation_language_detected",
            "Persisted explanation layer uses causation language where only correlation "
            "context is allowed.",
            source_reference,
            {"observedPhrases": observed},
        )
    ]


def unsupported_numeric_findings(
    artifacts: ExplanationComparisonArtifacts,
    output_text: str,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    allowed_numbers = collect_allowed_numbers(artifact_payload(artifacts))
    unsupported = []
    for value in set(NUMERIC_PATTERN.findall(output_text.lower())):
        normalized = normalize_number(value)
        if normalized and normalized not in allowed_numbers:
            unsupported.append(value)
    if not unsupported:
        return []
    return [
        finding(
            ExplanationComparisonFindingType.UNSUPPORTED_CLAIM,
            ExplanationComparisonSeverity.MEDIUM,
            "unsupported_numeric_claim",
            "Persisted explanation layer mentions numeric values not found in compared "
            "persisted artifacts.",
            source_reference,
            {"numericValues": sorted(unsupported)[:20]},
        )
    ]


def scenario_action_findings(
    artifacts: ExplanationComparisonArtifacts,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    unsupported_actions = sorted(
        {
            action
            for scenario in artifacts.scenarios
            for action in scenario.suggested_backend_actions_json
            if action not in ALLOWED_BACKEND_ACTIONS
        }
    )
    if not unsupported_actions:
        return []
    return [
        finding(
            ExplanationComparisonFindingType.UNSAFE_LANGUAGE,
            ExplanationComparisonSeverity.HIGH,
            "unsupported_scenario_action",
            "Scenario reasoning includes suggested actions outside the backend-safe action "
            "allowlist.",
            source_reference,
            {"unsupportedActions": unsupported_actions},
        )
    ]


def scenario_signal_contradiction_findings(
    artifacts: ExplanationComparisonArtifacts,
    source_reference: str,
) -> list[ComparisonFindingDraft]:
    signal = artifacts.signal
    if signal is None or signal.classification_status != "signal":
        return []
    primary = artifacts.scenarios[0] if artifacts.scenarios else None
    if primary is None:
        return []
    if (
        primary.scenario_type in {"reversal", "fakeout_risk"}
        and primary.possibility_label == "high"
    ):
        return [
            finding(
                ExplanationComparisonFindingType.CONTRADICTION,
                ExplanationComparisonSeverity.MEDIUM,
                "scenario_action_mismatch",
                "Primary scenario reasoning emphasizes a high-possibility reversal or "
                "fakeout against the final directional signal.",
                source_reference,
                {
                    "signalBias": signal.bias,
                    "scenarioType": primary.scenario_type,
                    "possibilityLabel": primary.possibility_label,
                },
            )
        ]
    return []


def score_findings(findings: list[ComparisonFindingDraft]) -> Decimal:
    penalty = sum(
        (SEVERITY_PENALTIES.get(finding.severity, Decimal("0.0000")) for finding in findings),
        Decimal("0.0000"),
    )
    return quantize_score(max(Decimal("0.0000"), Decimal("1.0000") - penalty))


def alignment_label_for(
    score: Decimal,
    findings: list[ComparisonFindingDraft],
    artifacts: ExplanationComparisonArtifacts,
    alignment_threshold: Decimal,
    review_threshold: Decimal,
) -> str:
    if artifacts.signal is None or artifacts.deterministic_explanation is None:
        return ExplanationAlignmentLabel.INSUFFICIENT_CONTEXT.value
    if artifacts.llm_explanation is None and artifacts.reasoning_run is None:
        return ExplanationAlignmentLabel.INSUFFICIENT_CONTEXT.value
    if any(
        finding.severity == ExplanationComparisonSeverity.CRITICAL.value
        for finding in findings
    ):
        return ExplanationAlignmentLabel.CONFLICTING.value
    if score < review_threshold or any(
        finding.finding_type == ExplanationComparisonFindingType.CONTRADICTION.value
        and finding.severity in REVIEW_SEVERITIES
        for finding in findings
    ):
        return ExplanationAlignmentLabel.CONFLICTING.value
    if score < alignment_threshold:
        return ExplanationAlignmentLabel.MIXED.value
    if findings:
        return ExplanationAlignmentLabel.MOSTLY_ALIGNED.value
    return ExplanationAlignmentLabel.ALIGNED.value


def comparison_metadata(
    artifacts: ExplanationComparisonArtifacts,
    findings: list[ComparisonFindingDraft],
    alignment_threshold: Decimal,
    review_threshold: Decimal,
    operator_review_recommended: bool,
) -> dict[str, object]:
    counts_by_severity: dict[str, int] = {}
    counts_by_type: dict[str, int] = {}
    for item in findings:
        counts_by_severity[item.severity] = counts_by_severity.get(item.severity, 0) + 1
        counts_by_type[item.finding_type] = counts_by_type.get(item.finding_type, 0) + 1
    return {
        "deterministicOnly": True,
        "llmProviderCalls": False,
        "explanationMutation": False,
        "signalMutation": False,
        "classificationMutation": False,
        "operatorReviewRecommended": operator_review_recommended,
        "alignmentThreshold": str(quantize_score(alignment_threshold)),
        "reviewThreshold": str(quantize_score(review_threshold)),
        "findingCountsBySeverity": counts_by_severity,
        "findingCountsByType": counts_by_type,
        "artifactAvailability": {
            "signal": artifacts.signal is not None,
            "deterministicExplanation": artifacts.deterministic_explanation is not None,
            "llmExplanation": artifacts.llm_explanation is not None,
            "reasoningRun": artifacts.reasoning_run is not None,
            "scenarioCount": len(artifacts.scenarios),
            "riskNoteCount": len(artifacts.risk_notes),
            "evidenceCount": len(artifacts.evidence),
            "newsCorrelationCount": len(artifacts.news_correlations),
            "scenarioEnsemble": artifacts.scenario_ensemble_run is not None,
        },
    }


def summary_for(
    label: str,
    score: Decimal,
    findings: list[ComparisonFindingDraft],
    operator_review_recommended: bool,
) -> str:
    if not findings:
        return f"Explanation layers are aligned with score {score}."
    top_codes = ", ".join(finding.code for finding in findings[:3])
    review_text = " Operator review is recommended." if operator_review_recommended else ""
    return (
        f"Explanation comparison is {label} with score {score}; "
        f"key findings: {top_codes}.{review_text}"
    )


def finding(
    finding_type: ExplanationComparisonFindingType,
    severity: ExplanationComparisonSeverity,
    code: str,
    message: str,
    source_reference: str | None = None,
    metadata_json: dict[str, object] | None = None,
) -> ComparisonFindingDraft:
    return ComparisonFindingDraft(
        finding_type=finding_type.value,
        severity=severity.value,
        code=code,
        message=message,
        source_reference=source_reference,
        metadata_json=metadata_json or {},
    )


def normalize_text(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


def json_text(value: object) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def nested_string(payload: dict[str, Any], key: str) -> str | None:
    if key in payload and isinstance(payload[key], str):
        return payload[key]
    for value in payload.values():
        if isinstance(value, dict):
            nested = nested_string(value, key)
            if nested is not None:
                return nested
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    nested = nested_string(item, key)
                    if nested is not None:
                        return nested
    return None


def source_reference_for(kind: str, identifier: object) -> str:
    return f"{kind}:{identifier}"


def contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(phrase_in_text(text, term) for term in terms)


def phrase_in_text(text: str, phrase: str) -> bool:
    return re.search(rf"\b{re.escape(phrase)}\b", text) is not None


def mentioned_pattern_keys(text: str) -> set[str]:
    mentioned: set[str] = set()
    for pattern_key, terms in PATTERN_TERMS.items():
        if any(phrase_in_text(text, term) for term in terms):
            mentioned.add(pattern_key)
    return mentioned


def mentions_news(text: str) -> bool:
    return any(phrase_in_text(text, keyword) for keyword in NEWS_KEYWORDS)


def news_descriptors(artifacts: ExplanationComparisonArtifacts) -> set[str]:
    descriptors: set[str] = set()
    for correlation in artifacts.news_correlations:
        metadata = correlation.metadata_json or {}
        for value in metadata.values():
            if isinstance(value, str):
                normalized = normalize_text(value)
                if normalized:
                    descriptors.add(normalized)
        descriptors.add(normalize_text(correlation.correlation_label))
        descriptors.add(normalize_text(correlation.reason))
    return {descriptor for descriptor in descriptors if len(descriptor) >= 3}


def text_mentions_risk_note(text: str, code: str, message: str) -> bool:
    code_tokens = set(WORD_PATTERN.findall(normalize_text(code)))
    message_tokens = {
        token
        for token in WORD_PATTERN.findall(normalize_text(message))
        if len(token) >= 5 and token not in {"risk", "signal", "market", "notes"}
    }
    text_tokens = set(WORD_PATTERN.findall(text))
    if code_tokens and code_tokens & text_tokens:
        return True
    if not message_tokens:
        return False
    overlap = message_tokens & text_tokens
    return len(overlap) >= min(2, len(message_tokens))


def scenario_text(artifacts: ExplanationComparisonArtifacts) -> str:
    parts: list[str] = []
    for scenario in artifacts.scenarios:
        parts.extend(
            [
                scenario.scenario_type,
                scenario.scenario_label,
                scenario.possibility_label,
                " ".join(scenario.supporting_evidence_json),
                " ".join(scenario.conflicting_evidence_json),
                " ".join(scenario.next_observations_json),
                " ".join(scenario.suggested_backend_actions_json),
                " ".join(scenario.risk_notes_json),
                json_text(scenario.outcome_history_json or {}),
            ]
        )
    return " ".join(parts)


def artifact_payload(artifacts: ExplanationComparisonArtifacts) -> dict[str, object]:
    signal = artifacts.signal
    deterministic = artifacts.deterministic_explanation
    return {
        "signal": {
            "bias": signal.bias if signal else None,
            "patternType": signal.pattern_type if signal else None,
            "classificationStatus": signal.classification_status if signal else None,
            "confidenceScore": str(signal.confidence_score) if signal else None,
            "candidateStrength": (
                str(signal.candidate_strength)
                if signal and signal.candidate_strength is not None
                else None
            ),
            "pipsMoved": str(signal.pips_moved) if signal and signal.pips_moved else None,
            "tickMoved": str(signal.tick_moved) if signal and signal.tick_moved else None,
            "summary": signal.summary if signal else None,
        },
        "evidence": [
            {
                "message": item.message,
                "numericValue": str(item.numeric_value) if item.numeric_value is not None else None,
                "weight": str(item.weight),
                "metadata": item.metadata_json,
            }
            for item in artifacts.evidence
        ],
        "riskNotes": [
            {"code": note.code, "message": note.message, "severity": note.severity}
            for note in artifacts.risk_notes
        ],
        "deterministicExplanation": {
            "shortSummary": deterministic.short_summary if deterministic else None,
            "marketBehavior": deterministic.market_behavior if deterministic else None,
            "evidenceSummary": deterministic.evidence_summary if deterministic else None,
            "confidenceSummary": deterministic.confidence_summary if deterministic else None,
            "riskSummary": deterministic.risk_summary if deterministic else None,
            "fullText": deterministic.full_text if deterministic else None,
            "sourceSnapshot": deterministic.source_snapshot_json if deterministic else None,
        },
        "newsCorrelations": [
            {
                "correlationScore": str(item.correlation_score),
                "timeDeltaMinutes": str(item.time_delta_minutes),
                "reason": item.reason,
                "metadata": item.metadata_json,
            }
            for item in artifacts.news_correlations
        ],
        "reasoningInput": (
            artifacts.reasoning_run.input_snapshot_json if artifacts.reasoning_run else None
        ),
        "scenarioEnsembleMetadata": (
            artifacts.scenario_ensemble_run.metadata_json
            if artifacts.scenario_ensemble_run is not None
            else None
        ),
    }


def collect_allowed_numbers(value: object) -> set[str]:
    numbers: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if "time" in key_text or key_text.endswith("id") or key_text.endswith("at"):
                continue
            numbers.update(collect_allowed_numbers(item))
    elif isinstance(value, list):
        for item in value:
            numbers.update(collect_allowed_numbers(item))
    elif isinstance(value, str):
        for match in NUMERIC_PATTERN.findall(value):
            normalized = normalize_number(match)
            if normalized:
                numbers.add(normalized)
    elif isinstance(value, int | float | Decimal):
        normalized = normalize_number(str(value))
        if normalized:
            numbers.add(normalized)
    return numbers


def normalize_number(value: str) -> str:
    try:
        normalized = str(Decimal(value).normalize())
    except (InvalidOperation, ValueError):
        return ""
    if normalized in {"-0", "0E+0"}:
        return "0"
    return normalized


def quantize_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
