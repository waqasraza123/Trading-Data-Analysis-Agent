from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.explanations.models import DeterministicExplanation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.intelligence_reports.repository import IntelligenceReportRepository
from app.modules.intelligence_reports.schemas import (
    IntelligenceReportOptions,
    IntelligenceReportRead,
    IntelligenceReportSubject,
    IntelligenceReportSubjectType,
    IntelligenceReportType,
)
from app.modules.intelligence_reports.sections import (
    MAX_ACTION_ITEMS,
    MAX_AUDIT_EVENTS,
    MAX_CORRELATIONS,
    MAX_DIAGNOSTICS,
    MAX_PATTERN_CANDIDATES,
    MAX_RECOMMENDATIONS,
    MAX_SCENARIO_HYPOTHESES,
    SAFE_OUTCOME_TERMS,
    bounded_items,
    bounded_mapping_items,
    grouped_evidence,
    summarize_json_snapshot,
    to_report_value,
)
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.news.models import NewsEvent, SignalNewsCorrelation
from app.modules.outcomes.aggregator import OutcomeAggregator
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.symbols.models import Symbol

DEFAULT_HISTORICAL_HORIZONS = [5, 15, 30, 60]


class IntelligenceReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = IntelligenceReportRepository(session)
        self.aggregator = OutcomeAggregator()

    async def build_signal_report(
        self,
        signal_id: UUID,
        options: IntelligenceReportOptions | None = None,
    ) -> IntelligenceReportRead:
        resolved_options = options or IntelligenceReportOptions()
        signal = await self.get_signal(signal_id)
        symbol = await self.repository.get_symbol(signal.symbol_id)
        missing_sections: list[str] = []
        warnings: list[str] = []
        components = await self.repository.list_confidence_components(signal.id)
        evidence = await self.repository.list_evidence(signal.id)
        risk_notes = await self.repository.list_risk_notes(signal.id)
        explanation = await self.repository.get_deterministic_explanation_by_signal_id(signal.id)
        correlations = await self.repository.list_news_correlations_by_signal_id(signal.id)
        news_events = await self.news_events_for_correlations(correlations)
        llm_explanation = await self.repository.get_llm_explanation_by_signal_id(signal.id)
        reasoning_run = (
            await self.repository.get_latest_reasoning_run_by_signal_id(signal.id)
            if resolved_options.include_reasoning
            else None
        )
        scenarios = (
            await self.repository.list_scenario_hypotheses(reasoning_run.id)
            if reasoning_run is not None
            else []
        )
        action_plan = await self.resolve_signal_action_plan(
            signal=signal,
            reasoning_run=reasoning_run,
            include_actions=resolved_options.include_actions,
        )
        action_items = (
            await self.repository.list_action_items(action_plan.id)
            if action_plan is not None
            else []
        )
        outcomes = (
            await self.repository.list_signal_outcomes(signal.id)
            if resolved_options.include_outcomes
            else []
        )
        audit_logs = (
            await self.repository.list_audit_logs(signal.analysis_run_id)
            if resolved_options.include_audit
            else []
        )
        screenshot_runs = await self.repository.list_chart_screenshot_runs_by_analysis_run_id(
            signal.analysis_run_id
        )
        sections: dict[str, Any] = {
            "summary": self.signal_summary(signal, symbol),
            "evidence": self.evidence_section(evidence, resolved_options.limit_evidence),
            "confidence": self.confidence_section(signal, components),
            "risk": self.risk_section(signal, risk_notes),
            "deterministic_explanation": self.deterministic_explanation_section(
                explanation,
                missing_sections,
            ),
            "news_correlation": self.news_correlation_section(
                correlations,
                news_events,
                missing_sections,
            ),
            "llm_explanation": self.llm_explanation_section(llm_explanation, missing_sections),
            "scenario_reasoning": self.scenario_reasoning_section(
                reasoning_run,
                scenarios,
                missing_sections,
                resolved_options.include_reasoning,
            ),
            "action_plan": self.action_plan_section(
                action_plan,
                action_items,
                missing_sections,
                resolved_options.include_actions,
            ),
            "outcomes": self.outcomes_section(
                outcomes,
                missing_sections,
                resolved_options.include_outcomes,
            ),
            "historical_behavior": await self.historical_behavior_section(
                signal=signal,
                outcomes=outcomes,
                missing_sections=missing_sections,
                include_diagnostics=resolved_options.include_diagnostics,
            ),
            "audit": self.audit_section(
                audit_logs,
                missing_sections,
                resolved_options.include_audit,
                resolved_options.limit_audit,
            ),
            "human_review": self.human_review_section(screenshot_runs, missing_sections),
        }
        return self.report(
            report_type=IntelligenceReportType.SIGNAL_REPORT,
            workspace_id=signal.workspace_id,
            subject_type=IntelligenceReportSubjectType.SIGNAL,
            subject_id=signal.id,
            sections=sections,
            warnings=warnings,
            missing_sections=missing_sections,
        )

    async def build_analysis_run_report(
        self,
        analysis_run_id: UUID,
        options: IntelligenceReportOptions | None = None,
    ) -> IntelligenceReportRead:
        resolved_options = options or IntelligenceReportOptions()
        run = await self.get_analysis_run(analysis_run_id)
        symbol = await self.repository.get_symbol(run.symbol_id)
        signal = await self.repository.get_signal_by_analysis_run_id(run.id)
        feature_snapshot = await self.repository.get_feature_snapshot(run.id)
        indicator_snapshot = await self.repository.get_indicator_snapshot(run.id)
        candidates = await self.repository.list_pattern_candidates(run.id)
        explanation = await self.repository.get_deterministic_explanation_by_analysis_run_id(run.id)
        correlations = await self.repository.list_news_correlations_by_analysis_run_id(run.id)
        news_events = await self.news_events_for_correlations(correlations)
        outcomes = (
            await self.repository.list_analysis_outcomes(run.id)
            if resolved_options.include_outcomes
            else []
        )
        audit_logs = (
            await self.repository.list_audit_logs(run.id) if resolved_options.include_audit else []
        )
        action_plan = (
            await self.repository.get_latest_action_plan_by_analysis_run_id(run.id)
            if resolved_options.include_actions
            else None
        )
        action_items = (
            await self.repository.list_action_items(action_plan.id)
            if action_plan is not None
            else []
        )
        missing_sections: list[str] = []
        sections: dict[str, Any] = {
            "analysis_run": self.analysis_run_section(run, symbol),
            "candle_source_context": await self.candle_source_context(run),
            "feature_snapshot_summary": self.snapshot_section(feature_snapshot, "features_json"),
            "indicator_snapshot_summary": self.snapshot_section(
                indicator_snapshot,
                "indicators_json",
            ),
            "pattern_candidates": self.pattern_candidates_section(candidates),
            "signal": self.analysis_signal_section(signal, missing_sections),
            "deterministic_explanation": self.deterministic_explanation_section(
                explanation,
                missing_sections,
            ),
            "news_correlation": self.news_correlation_section(
                correlations,
                news_events,
                missing_sections,
            ),
            "outcomes": self.outcomes_section(
                outcomes,
                missing_sections,
                resolved_options.include_outcomes,
            ),
            "replay_metadata": self.replay_metadata_section(run),
            "action_plan": self.action_plan_section(
                action_plan,
                action_items,
                missing_sections,
                resolved_options.include_actions,
            ),
            "audit_timeline": self.audit_section(
                audit_logs,
                missing_sections,
                resolved_options.include_audit,
                resolved_options.limit_audit,
            ),
        }
        return self.report(
            report_type=IntelligenceReportType.ANALYSIS_RUN_REPORT,
            workspace_id=run.workspace_id,
            subject_type=IntelligenceReportSubjectType.ANALYSIS_RUN,
            subject_id=run.id,
            sections=sections,
            warnings=[],
            missing_sections=missing_sections,
        )

    async def build_reasoning_run_report(
        self,
        reasoning_run_id: UUID,
        options: IntelligenceReportOptions | None = None,
    ) -> IntelligenceReportRead:
        resolved_options = options or IntelligenceReportOptions()
        run = await self.repository.get_reasoning_run(reasoning_run_id)
        if run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        scenarios = await self.repository.list_scenario_hypotheses(run.id)
        signal = await self.repository.get_signal(run.signal_id) if run.signal_id else None
        action_plan = (
            await self.repository.get_latest_action_plan_by_reasoning_run_id(run.id)
            if resolved_options.include_actions
            else None
        )
        action_items = (
            await self.repository.list_action_items(action_plan.id)
            if action_plan is not None
            else []
        )
        audit_logs = (
            await self.repository.list_audit_logs(run.analysis_run_id)
            if resolved_options.include_audit and run.analysis_run_id is not None
            else []
        )
        missing_sections: list[str] = []
        sections: dict[str, Any] = {
            "reasoning_run": self.reasoning_run_section(run),
            "safety_grounding": self.reasoning_safety_section(run),
            "input_snapshot_summary": summarize_json_snapshot(run.input_snapshot_json),
            "scenario_hypotheses": self.scenarios_section(scenarios),
            "suggested_backend_actions": self.suggested_backend_actions_section(scenarios),
            "linked_signal": self.analysis_signal_section(signal, missing_sections),
            "action_plan": self.action_plan_section(
                action_plan,
                action_items,
                missing_sections,
                resolved_options.include_actions,
            ),
            "blocked_grounding_issues": {
                "blocked_terms": to_report_value(run.blocked_terms_json),
                "grounding_issues": to_report_value(run.grounding_issues_json),
                "error_message": to_report_value(run.error_message),
            },
            "audit_events": self.audit_section(
                audit_logs,
                missing_sections,
                resolved_options.include_audit,
                resolved_options.limit_audit,
            ),
        }
        return self.report(
            report_type=IntelligenceReportType.REASONING_RUN_REPORT,
            workspace_id=run.workspace_id,
            subject_type=IntelligenceReportSubjectType.REASONING_RUN,
            subject_id=run.id,
            sections=sections,
            warnings=[],
            missing_sections=missing_sections,
        )

    async def build_outcome_report(
        self,
        outcome_id: UUID | None = None,
        signal_id: UUID | None = None,
        options: IntelligenceReportOptions | None = None,
    ) -> IntelligenceReportRead:
        resolved_options = options or IntelligenceReportOptions()
        outcome = await self.repository.get_outcome(outcome_id) if outcome_id is not None else None
        resolved_signal_id = signal_id or (outcome.signal_id if outcome is not None else None)
        if resolved_signal_id is None:
            raise AppError(422, "outcome_subject_required", "Outcome or signal id is required")
        signal = await self.get_signal(resolved_signal_id)
        outcomes = await self.repository.list_signal_outcomes(signal.id)
        missing_sections: list[str] = []
        audit_logs = (
            await self.repository.list_audit_logs(signal.analysis_run_id)
            if resolved_options.include_audit
            else []
        )
        sections: dict[str, Any] = {
            "signal_summary": self.signal_summary(
                signal,
                await self.repository.get_symbol(signal.symbol_id),
            ),
            "outcomes_by_horizon": self.outcomes_section(outcomes, missing_sections, True),
            "reference_window": self.outcome_reference_section(outcome, outcomes),
            "aggregation_context": await self.historical_behavior_section(
                signal=signal,
                outcomes=outcomes,
                missing_sections=missing_sections,
                include_diagnostics=resolved_options.include_diagnostics,
            ),
            "historical_behavior_summary": {"safe_terms": list(SAFE_OUTCOME_TERMS)},
            "limitations": {
                "items": [
                    "Outcome reports describe observed final-candle behavior after classification.",
                    "Reports do not calculate broker accounting metrics or provide instructions.",
                    "Insufficient future candles are reported as insufficient data.",
                ]
            },
            "audit": self.audit_section(
                audit_logs,
                missing_sections,
                resolved_options.include_audit,
                resolved_options.limit_audit,
            ),
        }
        subject_id = outcome.id if outcome is not None else signal.id
        subject_type = (
            IntelligenceReportSubjectType.OUTCOME
            if outcome is not None
            else IntelligenceReportSubjectType.SIGNAL
        )
        return self.report(
            report_type=IntelligenceReportType.OUTCOME_REPORT,
            workspace_id=signal.workspace_id,
            subject_type=subject_type,
            subject_id=subject_id,
            sections=sections,
            warnings=[],
            missing_sections=missing_sections,
        )

    async def build_screenshot_decision_report(
        self,
        decision_id: UUID,
        options: IntelligenceReportOptions | None = None,
    ) -> IntelligenceReportRead:
        resolved_options = options or IntelligenceReportOptions()
        run = await self.repository.get_chart_screenshot_run(decision_id)
        if run is None:
            raise AppError(
                404,
                "screenshot_decision_not_found",
                "Screenshot decision was not found",
            )
        missing_sections: list[str] = []
        analysis_run = (
            await self.repository.get_analysis_run(run.analysis_run_id)
            if run.analysis_run_id is not None
            else None
        )
        signal = (
            await self.repository.get_signal_by_analysis_run_id(analysis_run.id)
            if analysis_run is not None
            else None
        )
        corrections = await self.repository.list_chart_corrections(run.id)
        audit_logs = (
            await self.repository.list_audit_logs(analysis_run.id)
            if resolved_options.include_audit and analysis_run is not None
            else []
        )
        sections: dict[str, Any] = {
            "source_screenshot": self.screenshot_source_section(run),
            "extracted_ohlc_context": self.screenshot_ohlc_context(run),
            "linked_analysis": (
                self.analysis_run_section(
                    analysis_run,
                    await self.repository.get_symbol(analysis_run.symbol_id),
                )
                if analysis_run is not None
                else self.missing("linked_analysis", missing_sections)
            ),
            "linked_signal": self.analysis_signal_section(signal, missing_sections),
            "human_review": self.human_review_section([run], missing_sections),
            "correction_lineage": self.correction_lineage_section(run, corrections),
            "audit": self.audit_section(
                audit_logs,
                missing_sections,
                resolved_options.include_audit,
                resolved_options.limit_audit,
            ),
        }
        return self.report(
            report_type=IntelligenceReportType.SCREENSHOT_DECISION_REPORT,
            workspace_id=run.workspace_id,
            subject_type=IntelligenceReportSubjectType.SCREENSHOT_DECISION,
            subject_id=run.id,
            sections=sections,
            warnings=[
                "Screenshot decision reports are read-only bundles of persisted "
                "screenshot artifacts."
            ],
            missing_sections=missing_sections,
        )

    async def get_signal(self, signal_id: UUID) -> Signal:
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        return signal

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        run = await self.repository.get_analysis_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        return run

    async def news_events_for_correlations(
        self,
        correlations: list[SignalNewsCorrelation],
    ) -> dict[UUID, NewsEvent]:
        events = await self.repository.list_news_events(
            [correlation.news_event_id for correlation in correlations]
        )
        return {event.id: event for event in events}

    async def resolve_signal_action_plan(
        self,
        signal: Signal,
        reasoning_run: LlmReasoningRun | None,
        include_actions: bool,
    ) -> ReasoningActionPlan | None:
        if not include_actions:
            return None
        if reasoning_run is not None:
            action_plan = await self.repository.get_latest_action_plan_by_reasoning_run_id(
                reasoning_run.id
            )
            if action_plan is not None:
                return action_plan
        return await self.repository.get_latest_action_plan_by_signal_id(signal.id)

    def report(
        self,
        report_type: IntelligenceReportType,
        workspace_id: UUID,
        subject_type: IntelligenceReportSubjectType,
        subject_id: UUID,
        sections: dict[str, Any],
        warnings: list[str],
        missing_sections: list[str],
    ) -> IntelligenceReportRead:
        safe_sections = to_report_value(sections)
        safe_warnings = to_report_value(warnings)
        return IntelligenceReportRead(
            report_type=report_type,
            generated_at=utc_now(),
            workspace_id=workspace_id,
            subject=IntelligenceReportSubject(type=subject_type, id=subject_id),
            sections=safe_sections if isinstance(safe_sections, dict) else {},
            warnings=(
                [str(item) for item in safe_warnings] if isinstance(safe_warnings, list) else []
            ),
            missing_sections=sorted(set(missing_sections)),
        )

    def signal_summary(self, signal: Signal, symbol: Symbol | None) -> dict[str, Any]:
        return {
            "signal_id": signal.id,
            "analysis_run_id": signal.analysis_run_id,
            "symbol": symbol.symbol if symbol is not None else None,
            "symbol_id": signal.symbol_id,
            "timeframe": signal.timeframe,
            "classification_status": signal.classification_status,
            "bias": signal.bias,
            "pattern_type": signal.pattern_type,
            "strategy_profile_key": signal.strategy_profile_key,
            "strategy_profile_version": signal.strategy_profile_version,
            "confidence_score": signal.confidence_score,
            "confidence_label": signal.confidence_label,
            "no_signal_reason": signal.no_signal_reason,
            "summary": signal.summary,
        }

    def evidence_section(
        self,
        evidence: list[SignalEvidence],
        limit: int,
    ) -> dict[str, Any]:
        return grouped_evidence([self.evidence_row(item) for item in evidence], limit)

    def confidence_section(
        self,
        signal: Signal,
        components: list[SignalConfidenceComponent],
    ) -> dict[str, Any]:
        highest = max(components, key=lambda item: item.weighted_score, default=None)
        weakest = min(components, key=lambda item: item.weighted_score, default=None)
        weighted_score = sum((component.weighted_score for component in components), Decimal("0"))
        return {
            "confidence_score": signal.confidence_score,
            "confidence_label": signal.confidence_label,
            "weighted_score": weighted_score,
            "highest_component": (
                self.confidence_component_row(highest) if highest is not None else None
            ),
            "weakest_component": (
                self.confidence_component_row(weakest) if weakest is not None else None
            ),
            "components": bounded_items(
                [self.confidence_component_row(component) for component in components],
                50,
            ),
            "confidence_explanation": (
                "; ".join(component.reason for component in components[:5]) if components else None
            ),
        }

    def risk_section(self, signal: Signal, risk_notes: list[SignalRiskNote]) -> dict[str, Any]:
        return {
            "risk_notes": bounded_items([self.risk_note_row(note) for note in risk_notes], 50),
            "no_signal_reason": signal.no_signal_reason,
            "no_signal_reason_mapping": self.no_signal_reason_mapping(signal.no_signal_reason),
        }

    def deterministic_explanation_section(
        self,
        explanation: DeterministicExplanation | None,
        missing_sections: list[str],
    ) -> dict[str, Any]:
        if explanation is None:
            return self.missing("deterministic_explanation", missing_sections)
        return {
            "id": explanation.id,
            "template_version": explanation.template_version,
            "explanation_type": explanation.explanation_type,
            "short_summary": explanation.short_summary,
            "market_behavior": explanation.market_behavior,
            "evidence_summary": explanation.evidence_summary,
            "confidence_summary": explanation.confidence_summary,
            "risk_summary": explanation.risk_summary,
            "no_signal_summary": explanation.no_signal_summary,
            "full_text": explanation.full_text,
            "safety_status": explanation.safety_status,
            "blocked_terms": explanation.blocked_terms_json,
            "created_at": explanation.created_at,
        }

    def news_correlation_section(
        self,
        correlations: list[SignalNewsCorrelation],
        news_events: dict[UUID, NewsEvent],
        missing_sections: list[str],
    ) -> dict[str, Any]:
        if not correlations:
            return self.missing("news_correlation", missing_sections)
        rows = [
            self.news_correlation_row(correlation, news_events.get(correlation.news_event_id))
            for correlation in correlations
        ]
        return {
            "correlation_count": len(correlations),
            "strongest_correlation": rows[0] if rows else None,
            "correlations": bounded_items(rows, MAX_CORRELATIONS),
            "language_policy": (
                "News/event rows are contextual correlations only and do not claim causation."
            ),
        }

    def llm_explanation_section(
        self,
        explanation: LlmExplanation | None,
        missing_sections: list[str],
    ) -> dict[str, Any]:
        if explanation is None:
            return self.missing("llm_explanation", missing_sections)
        safe_to_show_output = explanation.safety_status in {"passed", "fallback_used"}
        return {
            "id": explanation.id,
            "provider": explanation.provider,
            "model": explanation.model,
            "prompt_version": explanation.prompt_version,
            "safety_status": explanation.safety_status,
            "grounding_status": explanation.grounding_status,
            "grounding_issues": explanation.grounding_issues_json,
            "blocked_terms": explanation.blocked_terms_json,
            "output_text": explanation.output_text if safe_to_show_output else None,
            "unsafe_output_redacted": not safe_to_show_output,
            "tokens_input": explanation.tokens_input,
            "tokens_output": explanation.tokens_output,
            "estimated_cost": explanation.estimated_cost,
            "created_at": explanation.created_at,
        }

    def scenario_reasoning_section(
        self,
        run: LlmReasoningRun | None,
        scenarios: list[ScenarioHypothesis],
        missing_sections: list[str],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if run is None:
            return self.missing("scenario_reasoning", missing_sections)
        return {
            "latest_reasoning_run": self.reasoning_run_section(run),
            "scenario_hypotheses": self.scenarios_section(scenarios),
            "suggested_backend_actions": self.suggested_backend_actions_section(scenarios),
            "safety_status": run.safety_status,
            "grounding_status": run.grounding_status,
        }

    def action_plan_section(
        self,
        plan: ReasoningActionPlan | None,
        items: list[ReasoningActionItem],
        missing_sections: list[str],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if plan is None:
            return self.missing("action_plan", missing_sections)
        counts: dict[str, int] = {}
        due_count = 0
        now = utc_now()
        for item in items:
            counts[item.status] = counts.get(item.status, 0) + 1
            if item.due_at is not None and item.due_at <= now and item.status in {"pending", "due"}:
                due_count += 1
        return {
            "plan": self.action_plan_row(plan),
            "action_items": bounded_items(
                [self.action_item_row(item) for item in items],
                MAX_ACTION_ITEMS,
            ),
            "status_counts": counts,
            "due_count": due_count,
            "failed_count": counts.get("failed", 0),
            "skipped_count": counts.get("skipped", 0),
            "completed_count": counts.get("completed", 0),
            "rejected_actions": plan.metadata_json.get("rejectedActions", []),
            "skipped_actions": plan.metadata_json.get("skippedActions", []),
        }

    def outcomes_section(
        self,
        outcomes: list[SignalOutcome],
        missing_sections: list[str],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not outcomes:
            return self.missing("outcomes", missing_sections)
        return {
            "outcomes_by_horizon": bounded_items(
                [self.outcome_row(outcome) for outcome in outcomes],
                100,
            ),
            "safe_terms": list(SAFE_OUTCOME_TERMS),
            "not_directional_behavior": [
                self.outcome_row(outcome)
                for outcome in outcomes
                if outcome.outcome_label == "not_directional"
            ],
        }

    async def historical_behavior_section(
        self,
        signal: Signal,
        outcomes: list[SignalOutcome],
        missing_sections: list[str],
        include_diagnostics: bool,
    ) -> dict[str, Any]:
        horizons = (
            sorted({outcome.horizon_minutes for outcome in outcomes}) or DEFAULT_HISTORICAL_HORIZONS
        )
        aggregation: dict[str, Any] = {}
        for horizon in horizons:
            rows = await self.repository.list_historical_outcomes(
                workspace_id=signal.workspace_id,
                horizon_minutes=horizon,
                symbol_id=signal.symbol_id,
                timeframe=signal.timeframe,
                pattern_type=signal.pattern_type,
                strategy_profile_key=signal.strategy_profile_key,
            )
            aggregation[str(horizon)] = {
                "pattern": [
                    item.model_dump(mode="json")
                    for item in self.aggregator.aggregate_by_patterns(rows, horizon)
                ],
                "strategy_profile": [
                    item.model_dump(mode="json")
                    for item in self.aggregator.aggregate_by_strategy_profiles(rows, horizon)
                ],
                "symbol": [
                    item.model_dump(mode="json")
                    for item in self.aggregator.aggregate_by_symbols(rows, horizon)
                ],
            }
        diagnostics = await self.diagnostics_section(signal, missing_sections, include_diagnostics)
        return {
            "outcome_aggregation": aggregation,
            "profile_diagnostics": diagnostics["profile_diagnostics"],
            "pattern_diagnostics": diagnostics["pattern_diagnostics"],
            "calibration_recommendations": diagnostics["calibration_recommendations"],
        }

    async def diagnostics_section(
        self,
        signal: Signal,
        missing_sections: list[str],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {
                "profile_diagnostics": {"included": False},
                "pattern_diagnostics": {"included": False},
                "calibration_recommendations": {"included": False},
            }
        profile_diagnostics = await self.repository.list_optional_strategy_profile_diagnostics(
            workspace_id=signal.workspace_id,
            strategy_profile_key=signal.strategy_profile_key,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            limit=MAX_DIAGNOSTICS,
        )
        pattern_diagnostics = await self.repository.list_optional_pattern_diagnostics(
            workspace_id=signal.workspace_id,
            pattern_type=signal.pattern_type,
            strategy_profile_key=signal.strategy_profile_key,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            limit=MAX_DIAGNOSTICS,
        )
        recommendations = await self.repository.list_optional_calibration_recommendations(
            workspace_id=signal.workspace_id,
            strategy_profile_key=signal.strategy_profile_key,
            pattern_type=signal.pattern_type,
            symbol_id=signal.symbol_id,
            timeframe=signal.timeframe,
            limit=MAX_RECOMMENDATIONS,
        )
        if not profile_diagnostics and not pattern_diagnostics and not recommendations:
            missing_sections.append("historical_behavior.profile_diagnostics")
        return {
            "profile_diagnostics": bounded_mapping_items(profile_diagnostics, MAX_DIAGNOSTICS),
            "pattern_diagnostics": bounded_mapping_items(pattern_diagnostics, MAX_DIAGNOSTICS),
            "calibration_recommendations": bounded_mapping_items(
                recommendations,
                MAX_RECOMMENDATIONS,
            ),
        }

    def audit_section(
        self,
        audit_logs: list[AnalysisAuditLog],
        missing_sections: list[str],
        included: bool,
        limit: int,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not audit_logs:
            return self.missing("audit", missing_sections)
        return bounded_items(
            [self.audit_row(log) for log in audit_logs],
            min(limit, MAX_AUDIT_EVENTS),
        )

    def human_review_section(
        self,
        screenshot_runs: list[ChartScreenshotRun],
        missing_sections: list[str],
    ) -> dict[str, Any]:
        rows = [self.screenshot_review_row(run) for run in screenshot_runs]
        if not rows:
            return self.missing("human_review", missing_sections)
        return bounded_items(rows, 20)

    def analysis_run_section(self, run: AnalysisRun, symbol: Symbol | None) -> dict[str, Any]:
        return {
            "analysis_run_id": run.id,
            "workspace_id": run.workspace_id,
            "symbol_id": run.symbol_id,
            "symbol": symbol.symbol if symbol is not None else None,
            "source_id": run.source_id,
            "timeframe": run.timeframe,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "warmup_start_time": run.warmup_start_time,
            "baseline_start_time": run.baseline_start_time,
            "analysis_mode": run.analysis_mode,
            "status": run.status,
            "engine_version": run.engine_version,
            "rule_set_version": run.rule_set_version,
            "include_news_correlation": run.include_news_correlation,
            "include_ai_explanation": run.include_ai_explanation,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
        }

    async def candle_source_context(self, run: AnalysisRun) -> dict[str, Any]:
        return {
            "source_id": run.source_id,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "final_candle_count": await self.repository.count_candles_for_run(run),
            "raw_candle_series_included": False,
        }

    def snapshot_section(
        self,
        snapshot: FeatureSnapshot | IndicatorSnapshot | None,
        field_name: str,
    ) -> dict[str, Any]:
        if snapshot is None:
            return {"present": False}
        raw_snapshot = getattr(snapshot, field_name)
        return {
            "present": True,
            "id": snapshot.id,
            "created_at": snapshot.created_at,
            "summary": summarize_json_snapshot(raw_snapshot),
        }

    def pattern_candidates_section(
        self,
        candidates: list[PatternCandidate],
    ) -> dict[str, Any]:
        return bounded_items(
            [self.pattern_candidate_row(candidate) for candidate in candidates],
            MAX_PATTERN_CANDIDATES,
        )

    def analysis_signal_section(
        self,
        signal: Signal | None,
        missing_sections: list[str],
    ) -> dict[str, Any]:
        if signal is None:
            return self.missing("signal", missing_sections)
        return {
            "signal_id": signal.id,
            "analysis_run_id": signal.analysis_run_id,
            "classification_status": signal.classification_status,
            "bias": signal.bias,
            "pattern_type": signal.pattern_type,
            "confidence_score": signal.confidence_score,
            "confidence_label": signal.confidence_label,
            "summary": signal.summary,
            "signal_report_endpoint": f"/intelligence-reports/signals/{signal.id}",
        }

    def replay_metadata_section(self, run: AnalysisRun) -> dict[str, Any]:
        return {
            "is_replay": run.analysis_mode == "replay",
            "replayed_from_analysis_run_id": run.replayed_from_analysis_run_id,
            "replay_mode": run.replay_mode,
            "engine_snapshot": summarize_json_snapshot(run.engine_snapshot_json),
            "rule_set_snapshot": summarize_json_snapshot(run.rule_set_snapshot_json),
        }

    def reasoning_run_section(self, run: LlmReasoningRun) -> dict[str, Any]:
        output_summary = None
        if run.safety_status in {"passed", "fallback_used"} and isinstance(run.output_json, dict):
            output_summary = run.output_json.get("summary")
        return {
            "reasoning_run_id": run.id,
            "workspace_id": run.workspace_id,
            "analysis_run_id": run.analysis_run_id,
            "signal_id": run.signal_id,
            "outcome_id": run.outcome_id,
            "source_type": run.source_type,
            "provider": run.provider,
            "model": run.model,
            "prompt_version": run.prompt_version,
            "reasoning_type": run.reasoning_type,
            "status": run.status,
            "safety_status": run.safety_status,
            "grounding_status": run.grounding_status,
            "output_summary": output_summary,
            "unsafe_output_redacted": run.safety_status not in {"passed", "fallback_used"},
            "created_at": run.created_at,
            "updated_at": run.updated_at,
        }

    def reasoning_safety_section(self, run: LlmReasoningRun) -> dict[str, Any]:
        return {
            "safety_status": run.safety_status,
            "grounding_status": run.grounding_status,
            "blocked_terms": run.blocked_terms_json,
            "grounding_issues": run.grounding_issues_json,
            "error_message": run.error_message,
        }

    def scenarios_section(self, scenarios: list[ScenarioHypothesis]) -> dict[str, Any]:
        return bounded_items(
            [self.scenario_row(scenario) for scenario in scenarios],
            MAX_SCENARIO_HYPOTHESES,
        )

    def suggested_backend_actions_section(
        self,
        scenarios: list[ScenarioHypothesis],
    ) -> dict[str, Any]:
        actions: list[dict[str, Any]] = []
        for scenario in scenarios[:MAX_SCENARIO_HYPOTHESES]:
            for action in scenario.suggested_backend_actions_json:
                actions.append(
                    {
                        "scenario_id": scenario.id,
                        "scenario_type": scenario.scenario_type,
                        "action": action,
                    }
                )
        return bounded_items(actions, MAX_ACTION_ITEMS)

    def outcome_reference_section(
        self,
        outcome: SignalOutcome | None,
        outcomes: list[SignalOutcome],
    ) -> dict[str, Any]:
        source = outcome or (outcomes[0] if outcomes else None)
        if source is None:
            return {"present": False}
        return {
            "present": True,
            "reference_time": source.reference_time,
            "reference_price": source.reference_price,
            "future_window_start": source.future_window_start,
            "future_window_end": source.future_window_end,
            "future_candle_count": source.future_candle_count,
        }

    def screenshot_source_section(self, run: ChartScreenshotRun) -> dict[str, Any]:
        return {
            "chart_screenshot_run_id": run.id,
            "workspace_id": run.workspace_id,
            "source_id": run.source_id,
            "symbol_id": run.symbol_id,
            "analysis_run_id": run.analysis_run_id,
            "timeframe": run.timeframe,
            "file_name": run.file_name,
            "parser_name": run.parser_name,
            "parser_version": run.parser_version,
            "status": run.status,
            "extraction_confidence": run.extraction_confidence,
            "analysis_hypothesis": run.analysis_hypothesis,
            "analysis_hypothesis_confidence": run.analysis_hypothesis_confidence,
            "created_at": run.created_at,
            "completed_at": run.completed_at,
        }

    def screenshot_ohlc_context(self, run: ChartScreenshotRun) -> dict[str, Any]:
        trend_metrics = {}
        if isinstance(run.extracted_payload_json, dict):
            raw_metrics = run.extracted_payload_json.get("trendMetrics")
            if isinstance(raw_metrics, dict):
                trend_metrics = raw_metrics
        return {
            "raw_candle_count": run.raw_candle_count,
            "stored_candle_count": run.stored_candle_count,
            "duplicate_count": run.duplicate_count,
            "conflict_count": run.conflict_count,
            "extracted_window_start": run.extracted_window_start,
            "extracted_window_end": run.extracted_window_end,
            "trend_metrics": trend_metrics,
            "raw_candle_series_included": False,
            "warnings": run.extraction_warnings_json.get("warnings", []),
        }

    def correction_lineage_section(
        self,
        run: ChartScreenshotRun,
        corrections: list[ChartScreenshotRun],
    ) -> dict[str, Any]:
        return {
            "corrected_from_run_id": run.parser_metadata_json.get(
                "correctedFromChartScreenshotRunId"
            ),
            "correction_runs": bounded_items(
                [self.screenshot_source_section(item) for item in corrections],
                20,
            ),
        }

    def missing(self, section: str, missing_sections: list[str]) -> dict[str, Any]:
        missing_sections.append(section)
        return {"present": False, "missing": True}

    def evidence_row(self, item: SignalEvidence) -> dict[str, Any]:
        return {
            "id": item.id,
            "evidence_type": item.evidence_type,
            "support_direction": item.direction,
            "direction": item.direction,
            "weight": item.weight,
            "message": item.message,
            "numeric_value": item.numeric_value,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def confidence_component_row(self, item: SignalConfidenceComponent) -> dict[str, Any]:
        return {
            "id": item.id,
            "component_name": item.component_name,
            "component_score": item.component_score,
            "component_weight": item.component_weight,
            "weighted_score": item.weighted_score,
            "reason": item.reason,
            "created_at": item.created_at,
        }

    def risk_note_row(self, item: SignalRiskNote) -> dict[str, Any]:
        return {
            "id": item.id,
            "code": item.code,
            "severity": item.severity,
            "message": item.message,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def news_correlation_row(
        self,
        correlation: SignalNewsCorrelation,
        event: NewsEvent | None,
    ) -> dict[str, Any]:
        return {
            "id": correlation.id,
            "news_event_id": correlation.news_event_id,
            "event_title": event.title if event is not None else None,
            "event_time": event.event_time if event is not None else None,
            "event_type": event.event_type if event is not None else None,
            "importance": event.importance if event is not None else None,
            "currency": event.currency if event is not None else None,
            "asset": event.asset if event is not None else None,
            "correlation_score": correlation.correlation_score,
            "correlation_label": correlation.correlation_label,
            "direction_alignment": correlation.direction_alignment,
            "volatility_reaction": correlation.volatility_reaction,
            "time_delta_minutes": correlation.time_delta_minutes,
            "reason": correlation.reason,
            "metadata": correlation.metadata_json,
            "created_at": correlation.created_at,
        }

    def action_plan_row(self, plan: ReasoningActionPlan) -> dict[str, Any]:
        return {
            "id": plan.id,
            "source_type": plan.source_type,
            "source_id": plan.source_id,
            "signal_id": plan.signal_id,
            "analysis_run_id": plan.analysis_run_id,
            "reasoning_run_id": plan.reasoning_run_id,
            "status": plan.status,
            "plan_version": plan.plan_version,
            "created_from": plan.created_from,
            "summary": plan.summary,
            "metadata": plan.metadata_json,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
        }

    def action_item_row(self, item: ReasoningActionItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "action_plan_id": item.action_plan_id,
            "source_type": item.source_type,
            "source_id": item.source_id,
            "signal_id": item.signal_id,
            "analysis_run_id": item.analysis_run_id,
            "reasoning_run_id": item.reasoning_run_id,
            "action_type": item.action_type,
            "status": item.status,
            "priority": item.priority,
            "due_at": item.due_at,
            "horizon_minutes": item.horizon_minutes,
            "input": item.input_json,
            "result": item.result_json,
            "error_code": item.error_code,
            "error_message": item.error_message,
            "attempts": item.attempts,
            "max_attempts": item.max_attempts,
            "completed_at": item.completed_at,
        }

    def outcome_row(self, outcome: SignalOutcome) -> dict[str, Any]:
        return {
            "id": outcome.id,
            "horizon_minutes": outcome.horizon_minutes,
            "evaluation_status": outcome.evaluation_status,
            "reference_time": outcome.reference_time,
            "reference_price": outcome.reference_price,
            "future_window_start": outcome.future_window_start,
            "future_window_end": outcome.future_window_end,
            "future_candle_count": outcome.future_candle_count,
            "max_favorable_move": outcome.max_favorable_move,
            "max_adverse_move": outcome.max_adverse_move,
            "net_move": outcome.net_move,
            "max_favorable_pips": outcome.max_favorable_pips,
            "max_adverse_pips": outcome.max_adverse_pips,
            "net_pips": outcome.net_pips,
            "max_favorable_ticks": outcome.max_favorable_ticks,
            "max_adverse_ticks": outcome.max_adverse_ticks,
            "net_ticks": outcome.net_ticks,
            "direction_followed": outcome.direction_followed,
            "reversal_detected": outcome.reversal_detected,
            "outcome_label": outcome.outcome_label,
            "movement_quality": outcome.movement_quality,
            "evaluation_version": outcome.evaluation_version,
            "metadata": outcome.metadata_json,
            "created_at": outcome.created_at,
        }

    def pattern_candidate_row(self, candidate: PatternCandidate) -> dict[str, Any]:
        return {
            "id": candidate.id,
            "pattern_type": candidate.pattern_type,
            "bias": candidate.bias,
            "strength_score": candidate.strength_score,
            "is_selected": candidate.is_selected,
            "evidence": candidate.evidence_json,
            "risk_notes": candidate.risk_notes_json,
            "metrics": candidate.metrics_json,
            "created_at": candidate.created_at,
        }

    def scenario_row(self, scenario: ScenarioHypothesis) -> dict[str, Any]:
        return {
            "id": scenario.id,
            "scenario_type": scenario.scenario_type,
            "scenario_label": scenario.scenario_label,
            "possibility_label": scenario.possibility_label,
            "supporting_evidence": scenario.supporting_evidence_json,
            "conflicting_evidence": scenario.conflicting_evidence_json,
            "outcome_history": scenario.outcome_history_json,
            "next_observations": scenario.next_observations_json,
            "suggested_backend_actions": scenario.suggested_backend_actions_json,
            "risk_notes": scenario.risk_notes_json,
            "sort_order": scenario.sort_order,
            "created_at": scenario.created_at,
        }

    def audit_row(self, log: AnalysisAuditLog) -> dict[str, Any]:
        return {
            "id": log.id,
            "analysis_run_id": log.analysis_run_id,
            "event_type": log.event_type,
            "message": log.message,
            "metadata": log.metadata_json,
            "created_at": log.created_at,
        }

    def screenshot_review_row(self, run: ChartScreenshotRun) -> dict[str, Any]:
        review = run.parser_metadata_json.get("humanReview")
        return {
            "chart_screenshot_run_id": run.id,
            "analysis_run_id": run.analysis_run_id,
            "status": run.status,
            "human_review": review if isinstance(review, dict) else None,
            "corrected_from_run_id": run.parser_metadata_json.get(
                "correctedFromChartScreenshotRunId"
            ),
            "parser_name": run.parser_name,
            "created_at": run.created_at,
        }

    def no_signal_reason_mapping(self, reason: str | None) -> str | None:
        if reason is None:
            return None
        mappings = {
            "chop_or_sideways_market": "Market structure was classified as low-directional.",
            "conflicting_directional_candidates": "Opposing deterministic candidates were present.",
            "fakeout_risk": "Fakeout risk reduced deterministic signal quality.",
            "insufficient_evidence": "Persisted evidence did not clear deterministic thresholds.",
            "no_pattern_candidates": "No deterministic pattern candidates were persisted.",
            "no_profile_candidates": "No profile candidate was available for classification.",
        }
        return mappings.get(reason, "Deterministic classification did not produce a clean signal.")
