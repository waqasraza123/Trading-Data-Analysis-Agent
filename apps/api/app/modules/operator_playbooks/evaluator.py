from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.action_plans.models import ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.explanations.models import DeterministicExplanation
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.operator_playbooks.models import OperatorPlaybook
from app.modules.outcomes.models import SignalOutcome
from app.modules.profile_diagnostics.models import (
    PatternOutcomeDiagnostic,
    StrategyProfileDiagnostic,
)
from app.modules.reasoning.models import LlmReasoningRun
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)

SAFE_RECOMMENDED_ACTIONS = {
    "request_operator_review",
    "inspect_audit_timeline",
    "run_quality_check",
    "run_profile_diagnostics",
    "evaluate_outcomes",
    "inspect_deterministic_evidence",
    "inspect_readiness",
    "no_action",
}

REJECTED_ACTIONS = {
    "buy",
    "sell",
    "place_order",
    "use_leverage",
    "execute_trade",
    "open_position",
    "close_position",
}


@dataclass(frozen=True)
class OperatorPlaybookContext:
    workspace_id: UUID
    source_type: str
    source_id: UUID
    signal: Signal | None = None
    analysis_run: AnalysisRun | None = None
    readiness_assessment: DecisionReadinessAssessment | None = None
    outcome: SignalOutcome | None = None
    outcomes: list[SignalOutcome] = field(default_factory=list)
    reasoning_run: LlmReasoningRun | None = None
    chart_screenshot_run: ChartScreenshotRun | None = None
    action_plan: ReasoningActionPlan | None = None
    evidence: list[SignalEvidence] = field(default_factory=list)
    confidence_components: list[SignalConfidenceComponent] = field(default_factory=list)
    risk_notes: list[SignalRiskNote] = field(default_factory=list)
    deterministic_explanation: DeterministicExplanation | None = None
    llm_explanation: LlmExplanation | None = None
    profile_diagnostics: list[StrategyProfileDiagnostic] = field(default_factory=list)
    pattern_diagnostics: list[PatternOutcomeDiagnostic] = field(default_factory=list)
    audit_logs: list[AnalysisAuditLog] = field(default_factory=list)
    chart_screenshot_runs: list[ChartScreenshotRun] = field(default_factory=list)
    quality_findings: list[dict[str, object]] = field(default_factory=list)
    operator_reviews: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class OperatorPlaybookEvaluationResult:
    playbook_key: str
    playbook_version: str
    matched: bool
    severity: str
    title: str
    summary: str
    recommended_actions: list[str]
    evidence: dict[str, object]


class OperatorPlaybookEvaluator:
    def evaluate(
        self,
        playbook: OperatorPlaybook,
        context: OperatorPlaybookContext,
    ) -> OperatorPlaybookEvaluationResult:
        actions = validate_safe_actions(playbook.recommended_actions_json)
        matched = match_rule(playbook.trigger_rules_json, context)
        return OperatorPlaybookEvaluationResult(
            playbook_key=playbook.key,
            playbook_version=playbook.version,
            matched=matched,
            severity=playbook.severity,
            title=playbook.name,
            summary=build_summary(playbook, matched),
            recommended_actions=actions if matched else [],
            evidence=build_evidence(playbook, context, matched),
        )


def validate_safe_actions(actions: list[str]) -> list[str]:
    normalized_actions: list[str] = []
    for action in actions:
        if action in REJECTED_ACTIONS:
            continue
        if action not in SAFE_RECOMMENDED_ACTIONS:
            continue
        if action not in normalized_actions:
            normalized_actions.append(action)
    if not normalized_actions:
        return ["no_action"]
    if "no_action" in normalized_actions and len(normalized_actions) > 1:
        return [action for action in normalized_actions if action != "no_action"]
    return normalized_actions


def match_rule(rule: dict[str, object], context: OperatorPlaybookContext) -> bool:
    rule_type = str(rule.get("type", ""))
    if rule_type == "quality_inconsistent":
        return has_quality_inconsistency(context)
    if rule_type == "missing_evidence":
        return context.signal is not None and not context.evidence
    if rule_type == "blocked_readiness":
        assessment = context.readiness_assessment
        return assessment is not None and assessment.readiness_label == "blocked"
    if rule_type == "low_follow_through":
        return has_low_follow_through(context.outcomes)
    if rule_type == "low_confidence_chart_extraction":
        return has_low_confidence_chart_context(context)
    if rule_type == "blocked_llm_output":
        return has_blocked_llm_context(context)
    if rule_type == "ready_signal":
        assessment = context.readiness_assessment
        return (
            context.signal is not None
            and assessment is not None
            and assessment.readiness_label == "ready"
        )
    return False


def has_quality_inconsistency(context: OperatorPlaybookContext) -> bool:
    for finding in context.quality_findings:
        label = str(finding.get("label", "")).lower()
        code = str(finding.get("code", "")).lower()
        if "inconsistent" in label or "inconsistent" in code:
            return True
    for note in context.risk_notes:
        if "mismatch" in note.code or "inconsistent" in note.code:
            return True
    return False


def has_low_follow_through(outcomes: list[SignalOutcome]) -> bool:
    checked = [
        outcome
        for outcome in outcomes
        if outcome.evaluation_status == "evaluated"
        and outcome.outcome_label in {"no_follow_through", "reversal", "sideways_after_signal"}
    ]
    return len(checked) >= 2


def has_low_confidence_chart_context(context: OperatorPlaybookContext) -> bool:
    runs = list(context.chart_screenshot_runs)
    if context.chart_screenshot_run is not None:
        runs.append(context.chart_screenshot_run)
    for run in runs:
        if run.status == "review_required":
            return True
        if run.analysis_blocked_reason in {
            "low_extraction_confidence",
            "low_ocr_confidence",
            "axis_calibration_incomplete",
            "unsupported_chart_type",
        }:
            return True
        if run.extraction_confidence < Decimal("0.7500"):
            return True
    return False


def has_blocked_llm_context(context: OperatorPlaybookContext) -> bool:
    if context.llm_explanation is not None and context.llm_explanation.safety_status == "blocked":
        return True
    if context.reasoning_run is not None and context.reasoning_run.safety_status == "blocked":
        return True
    if context.readiness_assessment is None:
        return False
    blocker_codes = [
        str(blocker.get("code", ""))
        for blocker in context.readiness_assessment.blockers_json
        if isinstance(blocker, dict)
    ]
    return any("llm" in code and "blocked" in code for code in blocker_codes)


def build_summary(playbook: OperatorPlaybook, matched: bool) -> str:
    if matched:
        return playbook.description
    return "Playbook did not match the current persisted backend state."


def build_evidence(
    playbook: OperatorPlaybook,
    context: OperatorPlaybookContext,
    matched: bool,
) -> dict[str, object]:
    return {
        "matched": matched,
        "playbookKey": playbook.key,
        "sourceType": context.source_type,
        "sourceId": str(context.source_id),
        "signalId": str(context.signal.id) if context.signal is not None else None,
        "analysisRunId": (
            str(context.analysis_run.id) if context.analysis_run is not None else None
        ),
        "readinessLabel": (
            context.readiness_assessment.readiness_label
            if context.readiness_assessment is not None
            else None
        ),
        "evidenceCount": len(context.evidence),
        "confidenceComponentCount": len(context.confidence_components),
        "outcomeCount": len(context.outcomes),
        "auditLogCount": len(context.audit_logs),
        "chartScreenshotRunCount": len(context.chart_screenshot_runs),
        "qualityFindingCount": len(context.quality_findings),
        "operatorReviewCount": len(context.operator_reviews),
        "financialAdvice": False,
        "brokerExecution": False,
        "automaticExecution": False,
    }
