from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.decision_readiness.models import DecisionReadinessLabel
from app.modules.explanations.models import DeterministicExplanation, ExplanationSafetyStatus
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)

MISSING_REQUIRED_DEDUCTION = Decimal("0.20")
CRITICAL_BLOCKER_DEDUCTION = Decimal("0.35")
HIGH_SEVERITY_DEDUCTION = Decimal("0.20")
MEDIUM_WARNING_DEDUCTION = Decimal("0.10")
UNRESOLVED_HIGH_PRIORITY_REVIEW_DEDUCTION = Decimal("0.20")
PENDING_DUE_ACTION_ITEM_DEDUCTION = Decimal("0.10")
MISSING_OPTIONAL_CONTEXT_DEDUCTION = Decimal("0.03")

ALLOWED_NEXT_STEPS = {
    "run_quality_check",
    "review_evidence",
    "evaluate_outcome_after_horizon",
    "run_news_correlation",
    "request_human_review",
    "wait_for_more_final_candles",
    "inspect_audit_timeline",
    "no_action",
}


@dataclass(frozen=True)
class DecisionReadinessContext:
    source_type: str
    source_id: UUID
    signal: Signal | None
    analysis_run: AnalysisRun | None
    evidence: list[SignalEvidence] = field(default_factory=list)
    confidence_components: list[SignalConfidenceComponent] = field(default_factory=list)
    risk_notes: list[SignalRiskNote] = field(default_factory=list)
    deterministic_explanation: DeterministicExplanation | None = None
    llm_explanation: LlmExplanation | None = None
    news_correlations: list[SignalNewsCorrelation] = field(default_factory=list)
    outcomes: list[SignalOutcome] = field(default_factory=list)
    reasoning_runs: list[LlmReasoningRun] = field(default_factory=list)
    scenario_hypotheses: list[ScenarioHypothesis] = field(default_factory=list)
    action_plans: list[ReasoningActionPlan] = field(default_factory=list)
    open_action_items: list[ReasoningActionItem] = field(default_factory=list)
    audit_logs: list[AnalysisAuditLog] = field(default_factory=list)
    chart_screenshot_runs: list[ChartScreenshotRun] = field(default_factory=list)
    profile_diagnostics_count: int = 0
    historical_cases_count: int = 0
    quality_findings: list[dict[str, object]] = field(default_factory=list)
    operator_reviews: list[dict[str, object]] = field(default_factory=list)


@dataclass(frozen=True)
class DecisionReadinessResult:
    readiness_score: Decimal
    readiness_label: str
    required_checks: list[dict[str, object]]
    optional_checks: list[dict[str, object]]
    blockers: list[dict[str, object]]
    warnings: list[dict[str, object]]
    next_steps: list[str]
    summary: str
    metadata: dict[str, object]


class DecisionReadinessCalculator:
    def calculate(self, context: DecisionReadinessContext) -> DecisionReadinessResult:
        score = Decimal("1.0000")
        required_checks: list[dict[str, object]] = []
        optional_checks: list[dict[str, object]] = []
        blockers: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        next_steps: list[str] = []

        score = self.apply_required_checks(
            context,
            score,
            required_checks,
            blockers,
            warnings,
            next_steps,
        )
        score = self.apply_optional_checks(
            context,
            score,
            optional_checks,
            warnings,
            next_steps,
        )
        score = self.apply_risk_note_checks(context, score, warnings, next_steps)
        score = self.apply_llm_checks(
            context,
            score,
            required_checks,
            blockers,
            warnings,
            next_steps,
        )
        score = self.apply_chart_screenshot_checks(
            context,
            score,
            required_checks,
            blockers,
            warnings,
            next_steps,
        )
        score = self.apply_quality_checks(
            context,
            score,
            required_checks,
            blockers,
            warnings,
            next_steps,
        )
        score = self.apply_review_checks(
            context,
            score,
            required_checks,
            blockers,
            warnings,
            next_steps,
        )
        score = self.apply_action_item_checks(context, score, warnings, next_steps)
        score = clamp_score(score)
        label = choose_label(score, blockers)
        next_steps = normalize_next_steps(next_steps, label)
        summary = build_summary(label)
        metadata = {
            "sourceType": context.source_type,
            "sourceId": str(context.source_id),
            "analysisRunId": str(context.analysis_run.id) if context.analysis_run else None,
            "signalId": str(context.signal.id) if context.signal else None,
            "assessmentScope": "operator_consumption_readiness",
            "financialAdvice": False,
            "brokerExecution": False,
            "autoTrading": False,
        }
        return DecisionReadinessResult(
            readiness_score=score.quantize(Decimal("0.0001")),
            readiness_label=label,
            required_checks=required_checks,
            optional_checks=optional_checks,
            blockers=blockers,
            warnings=warnings,
            next_steps=next_steps,
            summary=summary,
            metadata=metadata,
        )

    def apply_required_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        required_checks: list[dict[str, object]],
        blockers: list[dict[str, object]],
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        if context.signal is None:
            score = add_required_missing(
                required_checks,
                blockers,
                score,
                "signal_exists",
                "Signal artifact is missing.",
                True,
            )
            next_steps.append("review_evidence")
        else:
            required_checks.append(passed_check("signal_exists", "Signal artifact exists."))
        if context.analysis_run is None:
            score = add_required_missing(
                required_checks,
                blockers,
                score,
                "analysis_run_exists",
                "Analysis run artifact is missing.",
                context.source_type == "analysis_run",
            )
            next_steps.append("inspect_audit_timeline")
        else:
            required_checks.append(passed_check("analysis_run_exists", "Analysis run exists."))
        if not context.evidence:
            score = add_required_missing(
                required_checks,
                blockers,
                score,
                "evidence_exists",
                "Signal is missing persisted evidence.",
                True,
            )
            next_steps.append("review_evidence")
        else:
            required_checks.append(passed_check("evidence_exists", "Persisted evidence exists."))
        if not context.confidence_components:
            score = add_required_missing(
                required_checks,
                blockers,
                score,
                "confidence_components_exist",
                "Signal is missing confidence support components.",
                True,
            )
            next_steps.append("review_evidence")
        else:
            required_checks.append(
                passed_check(
                    "confidence_components_exist",
                    "Confidence support components exist.",
                )
            )
        if context.deterministic_explanation is None:
            score = score - MISSING_REQUIRED_DEDUCTION
            required_checks.append(
                missing_check(
                    "deterministic_explanation_exists",
                    "Deterministic explanation is missing.",
                    MISSING_REQUIRED_DEDUCTION,
                )
            )
            warnings.append(
                warning_item(
                    "deterministic_explanation_missing",
                    "A grounded deterministic explanation is missing.",
                    "medium",
                )
            )
            next_steps.append("review_evidence")
        elif (
            context.deterministic_explanation.safety_status == ExplanationSafetyStatus.BLOCKED.value
        ):
            score = score - CRITICAL_BLOCKER_DEDUCTION
            required_checks.append(
                failed_check(
                    "deterministic_explanation_safe",
                    "Deterministic explanation safety fallback is active.",
                    CRITICAL_BLOCKER_DEDUCTION,
                )
            )
            blockers.append(
                blocker_item(
                    "deterministic_explanation_blocked",
                    "Deterministic explanation is blocked by safety checks.",
                    "critical",
                )
            )
            next_steps.append("review_evidence")
        else:
            required_checks.append(
                passed_check(
                    "deterministic_explanation_exists",
                    "Grounded deterministic explanation exists.",
                )
            )
        return score

    def apply_optional_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        optional_checks: list[dict[str, object]],
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        include_news = bool(
            context.analysis_run is not None and context.analysis_run.include_news_correlation
        )
        score = add_optional_presence_check(
            optional_checks,
            warnings,
            next_steps,
            score,
            include_news,
            bool(context.news_correlations),
            "news_correlation_exists",
            "News correlation was requested but no persisted correlation exists.",
            "run_news_correlation",
        )
        score = add_optional_presence_check(
            optional_checks,
            warnings,
            next_steps,
            score,
            True,
            bool(context.outcomes),
            "outcomes_exist",
            "No persisted outcome context exists for any horizon.",
            "evaluate_outcome_after_horizon",
        )
        score = add_optional_presence_check(
            optional_checks,
            warnings,
            next_steps,
            score,
            context.historical_cases_count > 0,
            context.historical_cases_count > 0,
            "historical_cases_exist",
            "Historical case adapter is unavailable or has no cases.",
            "no_action",
        )
        score = add_optional_presence_check(
            optional_checks,
            warnings,
            next_steps,
            score,
            True,
            context.profile_diagnostics_count > 0,
            "profile_diagnostics_exist",
            "No persisted profile diagnostic context was found.",
            "no_action",
        )
        reasoning_suggested_follow_up = any(
            has_backend_follow_up(hypothesis) for hypothesis in context.scenario_hypotheses
        )
        score = add_optional_presence_check(
            optional_checks,
            warnings,
            next_steps,
            score,
            reasoning_suggested_follow_up,
            bool(context.action_plans),
            "action_plan_exists",
            "Reasoning suggested follow-up, but no persisted action plan exists.",
            "request_human_review",
        )
        score = add_optional_presence_check(
            optional_checks,
            warnings,
            next_steps,
            score,
            True,
            bool(context.audit_logs),
            "audit_timeline_completeness",
            "Audit timeline context is empty.",
            "inspect_audit_timeline",
        )
        return score

    def apply_risk_note_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        for risk_note in context.risk_notes:
            if risk_note.severity == "high":
                score = score - HIGH_SEVERITY_DEDUCTION
                warnings.append(warning_item(risk_note.code, risk_note.message, "high"))
                next_steps.append("request_human_review")
            if risk_note.severity == "medium":
                score = score - MEDIUM_WARNING_DEDUCTION
                warnings.append(warning_item(risk_note.code, risk_note.message, "medium"))
        return score

    def apply_llm_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        required_checks: list[dict[str, object]],
        blockers: list[dict[str, object]],
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        explanation = context.llm_explanation
        if explanation is None:
            required_checks.append(
                passed_check(
                    "no_blocked_llm_grounding_issue",
                    "No blocked LLM artifact is linked.",
                )
            )
            return score
        if explanation.safety_status == "blocked":
            score = score - CRITICAL_BLOCKER_DEDUCTION
            required_checks.append(
                failed_check(
                    "no_blocked_llm_grounding_issue",
                    "A blocked LLM explanation artifact is linked.",
                    CRITICAL_BLOCKER_DEDUCTION,
                )
            )
            blockers.append(
                blocker_item(
                    "llm_output_blocked",
                    "A blocked LLM explanation artifact is linked to this source.",
                    "critical",
                )
            )
            next_steps.append("request_human_review")
        if explanation.grounding_status in {"failed", "questionable"}:
            score = score - HIGH_SEVERITY_DEDUCTION
            required_checks.append(
                failed_check(
                    "no_blocked_llm_grounding_issue",
                    "LLM explanation has unresolved grounding issues.",
                    HIGH_SEVERITY_DEDUCTION,
                )
            )
            warnings.append(
                warning_item(
                    "llm_grounding_issue",
                    "LLM explanation has unresolved grounding issues.",
                    "high",
                )
            )
            next_steps.append("review_evidence")
        if explanation.safety_status != "blocked" and explanation.grounding_status not in {
            "failed",
            "questionable",
        }:
            required_checks.append(
                passed_check(
                    "no_blocked_llm_grounding_issue",
                    "Linked LLM artifact has no blocked safety or grounding state.",
                )
            )
        return score

    def apply_chart_screenshot_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        required_checks: list[dict[str, object]],
        blockers: list[dict[str, object]],
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        if not context.chart_screenshot_runs:
            required_checks.append(
                passed_check(
                    "no_unsupported_chart_screenshot_source",
                    "No linked chart screenshot source requires blocking review.",
                )
            )
            return score
        for screenshot_run in context.chart_screenshot_runs:
            if screenshot_run.supported_for_analysis is False:
                score = score - CRITICAL_BLOCKER_DEDUCTION
                required_checks.append(
                    failed_check(
                        "no_unsupported_chart_screenshot_source",
                        "Linked chart screenshot source is unsupported for OHLC analysis.",
                        CRITICAL_BLOCKER_DEDUCTION,
                    )
                )
                blockers.append(
                    blocker_item(
                        "unsupported_chart_screenshot_source",
                        "Linked chart screenshot source is unsupported for OHLC analysis.",
                        "critical",
                    )
                )
                next_steps.append("request_human_review")
            if screenshot_requires_review(screenshot_run):
                if not screenshot_human_review_accepted(screenshot_run):
                    score = score - CRITICAL_BLOCKER_DEDUCTION
                    required_checks.append(
                        failed_check(
                            "screenshot_human_review_accepted",
                            "Low-confidence screenshot extraction needs accepted human review.",
                            CRITICAL_BLOCKER_DEDUCTION,
                        )
                    )
                    blockers.append(
                        blocker_item(
                            "screenshot_review_required",
                            "Low-confidence screenshot extraction requires accepted human review.",
                            "critical",
                        )
                    )
                    next_steps.append("request_human_review")
                else:
                    warnings.append(
                        warning_item(
                            "screenshot_review_accepted",
                            "Screenshot extraction required review and has accepted "
                            "review metadata.",
                            "medium",
                        )
                    )
        if not any(
            screenshot_run.supported_for_analysis is False
            or (
                screenshot_requires_review(screenshot_run)
                and not screenshot_human_review_accepted(screenshot_run)
            )
            for screenshot_run in context.chart_screenshot_runs
        ):
            required_checks.append(
                passed_check(
                    "no_unsupported_chart_screenshot_source",
                    "Linked chart screenshot sources have no blocking support issue.",
                )
            )
        return score

    def apply_quality_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        required_checks: list[dict[str, object]],
        blockers: list[dict[str, object]],
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        if not context.quality_findings:
            required_checks.append(
                passed_check(
                    "no_critical_quality_finding",
                    "No critical quality finding is present.",
                )
            )
            return score
        critical_found = False
        for finding in context.quality_findings:
            severity = str(finding.get("severity", "")).lower()
            message = str(finding.get("message", "Quality finding requires review."))
            if severity == "critical":
                critical_found = True
                score = score - CRITICAL_BLOCKER_DEDUCTION
                required_checks.append(
                    failed_check(
                        "no_critical_quality_finding",
                        message,
                        CRITICAL_BLOCKER_DEDUCTION,
                    )
                )
                blockers.append(blocker_item("critical_quality_finding", message, "critical"))
                next_steps.append("run_quality_check")
            elif severity == "high":
                score = score - HIGH_SEVERITY_DEDUCTION
                warnings.append(warning_item("high_quality_finding", message, "high"))
                next_steps.append("run_quality_check")
        if not critical_found:
            required_checks.append(
                passed_check(
                    "no_critical_quality_finding",
                    "No critical quality finding is present.",
                )
            )
        return score

    def apply_review_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        required_checks: list[dict[str, object]],
        blockers: list[dict[str, object]],
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        unresolved_reviews = [
            review
            for review in context.operator_reviews
            if str(review.get("status", "")).lower() not in {"resolved", "closed"}
        ]
        if not unresolved_reviews:
            required_checks.append(
                passed_check(
                    "no_unresolved_high_priority_review",
                    "No unresolved high-priority operator review is present.",
                )
            )
            return score
        for review in unresolved_reviews:
            priority = str(review.get("priority", "")).lower()
            severity = str(review.get("severity", "")).lower()
            message = str(review.get("message", "Operator review requires attention."))
            if severity == "critical":
                score = score - CRITICAL_BLOCKER_DEDUCTION
                required_checks.append(
                    failed_check(
                        "no_unresolved_high_priority_review",
                        message,
                        CRITICAL_BLOCKER_DEDUCTION,
                    )
                )
                blockers.append(
                    blocker_item("unresolved_critical_review_item", message, "critical")
                )
                next_steps.append("request_human_review")
            elif priority == "high":
                score = score - UNRESOLVED_HIGH_PRIORITY_REVIEW_DEDUCTION
                required_checks.append(
                    failed_check(
                        "no_unresolved_high_priority_review",
                        message,
                        UNRESOLVED_HIGH_PRIORITY_REVIEW_DEDUCTION,
                    )
                )
                warnings.append(warning_item("unresolved_high_priority_review", message, "high"))
                next_steps.append("request_human_review")
        return score

    def apply_action_item_checks(
        self,
        context: DecisionReadinessContext,
        score: Decimal,
        warnings: list[dict[str, object]],
        next_steps: list[str],
    ) -> Decimal:
        for item in context.open_action_items:
            if item.status in {"pending", "due", "running"}:
                score = score - PENDING_DUE_ACTION_ITEM_DEDUCTION
                warnings.append(
                    warning_item(
                        "pending_follow_up_action_item",
                        "A backend follow-up action item is still pending or due.",
                        "medium",
                    )
                )
                append_action_next_step(item.action_type, next_steps)
        return score


def add_required_missing(
    required_checks: list[dict[str, object]],
    blockers: list[dict[str, object]],
    score: Decimal,
    code: str,
    message: str,
    hard_blocker: bool,
) -> Decimal:
    required_checks.append(missing_check(code, message, MISSING_REQUIRED_DEDUCTION))
    if hard_blocker:
        blockers.append(blocker_item(code, message, "critical"))
    return score - MISSING_REQUIRED_DEDUCTION


def add_optional_presence_check(
    optional_checks: list[dict[str, object]],
    warnings: list[dict[str, object]],
    next_steps: list[str],
    score: Decimal,
    applies: bool,
    present: bool,
    code: str,
    missing_message: str,
    next_step: str,
) -> Decimal:
    if not applies:
        optional_checks.append(
            {
                "code": code,
                "status": "not_applicable",
                "message": "Optional context is not applicable for this source.",
                "deduction": "0.0000",
            }
        )
        return score
    if present:
        optional_checks.append(
            {
                "code": code,
                "status": "passed",
                "message": "Optional context exists.",
                "deduction": "0.0000",
            }
        )
        return score
    optional_checks.append(
        {
            "code": code,
            "status": "missing",
            "message": missing_message,
            "deduction": str(MISSING_OPTIONAL_CONTEXT_DEDUCTION),
        }
    )
    warnings.append(warning_item(code, missing_message, "low"))
    next_steps.append(next_step)
    return score - MISSING_OPTIONAL_CONTEXT_DEDUCTION


def passed_check(code: str, message: str) -> dict[str, object]:
    return {"code": code, "status": "passed", "message": message, "deduction": "0.0000"}


def missing_check(code: str, message: str, deduction: Decimal) -> dict[str, object]:
    return {"code": code, "status": "missing", "message": message, "deduction": str(deduction)}


def failed_check(code: str, message: str, deduction: Decimal) -> dict[str, object]:
    return {"code": code, "status": "failed", "message": message, "deduction": str(deduction)}


def blocker_item(code: str, message: str, severity: str) -> dict[str, object]:
    return {"code": code, "message": message, "severity": severity}


def warning_item(code: str, message: str, severity: str) -> dict[str, object]:
    return {"code": code, "message": message, "severity": severity}


def has_backend_follow_up(hypothesis: ScenarioHypothesis) -> bool:
    return any(str(action) != "no_action" for action in hypothesis.suggested_backend_actions_json)


def screenshot_requires_review(screenshot_run: ChartScreenshotRun) -> bool:
    if screenshot_run.status == "review_required":
        return True
    return screenshot_run.analysis_blocked_reason in {
        "low_extraction_confidence",
        "low_ocr_confidence",
        "axis_calibration_incomplete",
    }


def screenshot_human_review_accepted(screenshot_run: ChartScreenshotRun) -> bool:
    review = screenshot_run.parser_metadata_json.get("humanReview")
    if not isinstance(review, dict):
        return False
    return str(review.get("status", "")).lower() == "accepted"


def append_action_next_step(action_type: str, next_steps: list[str]) -> None:
    mapping = {
        "evaluate_outcome_after_horizon": "evaluate_outcome_after_horizon",
        "run_news_correlation": "run_news_correlation",
        "wait_for_more_final_candles": "wait_for_more_final_candles",
        "request_human_review": "request_human_review",
        "no_action": "no_action",
    }
    next_steps.append(mapping.get(action_type, "request_human_review"))


def normalize_next_steps(next_steps: list[str], label: str) -> list[str]:
    normalized: list[str] = []
    for next_step in next_steps:
        if next_step not in ALLOWED_NEXT_STEPS:
            continue
        if next_step == "no_action" and len(next_steps) > 1:
            continue
        if next_step not in normalized:
            normalized.append(next_step)
    if not normalized and label == DecisionReadinessLabel.READY.value:
        return ["no_action"]
    if not normalized:
        return ["review_evidence"]
    return normalized


def clamp_score(score: Decimal) -> Decimal:
    if score < Decimal("0"):
        return Decimal("0")
    if score > Decimal("1"):
        return Decimal("1")
    return score


def choose_label(score: Decimal, blockers: list[dict[str, object]]) -> str:
    if blockers:
        return DecisionReadinessLabel.BLOCKED.value
    if score >= Decimal("0.85"):
        return DecisionReadinessLabel.READY.value
    if score >= Decimal("0.55"):
        return DecisionReadinessLabel.REVIEW_RECOMMENDED.value
    return DecisionReadinessLabel.INSUFFICIENT_CONTEXT.value


def build_summary(label: str) -> str:
    if label == DecisionReadinessLabel.READY.value:
        return (
            "Source has required evidence, confidence support, explanation grounding, "
            "and no blocking findings for operator consumption."
        )
    if label == DecisionReadinessLabel.BLOCKED.value:
        return "Assessment is blocked because required traceability or safety evidence is missing."
    if label == DecisionReadinessLabel.REVIEW_RECOMMENDED.value:
        return (
            "Source has core readiness support, but review or follow-up context is still "
            "recommended."
        )
    return "Source does not have enough persisted backend context for operator consumption."
