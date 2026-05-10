from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.audit_timeline.collectors import (
    ArtifactGraphBuilder,
    bounded_artifacts,
    bounded_timeline,
    completeness_from_components,
    safe_metadata,
    timeline_event,
    to_timeline_value,
)
from app.modules.audit_timeline.repository import AuditTimelineRepository
from app.modules.audit_timeline.schemas import (
    ArtifactGraph,
    ArtifactRelationship,
    AuditTimelineCompleteness,
    AuditTimelineEvent,
    AuditTimelineOptions,
    AuditTimelineRead,
    AuditTimelineSeverity,
    AuditTimelineSubject,
    AuditTimelineSubjectType,
)
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.explanations.models import DeterministicExplanation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.intelligence_quality.models import (
    IntelligenceQualityFinding,
    IntelligenceQualityRun,
    ShadowClassificationResult,
)
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.market_scans.models import ScheduledScanRun, ScheduledScanRunItem
from app.modules.news.models import SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)


class AuditTimelineService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = AuditTimelineRepository(session)

    async def build_analysis_run_timeline(
        self,
        analysis_run_id: UUID,
        options: AuditTimelineOptions | None = None,
    ) -> AuditTimelineRead:
        resolved_options = options or AuditTimelineOptions()
        run = await self.repository.get_analysis_run(analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Analysis run not found")
        context = await self.analysis_context(run, resolved_options)
        events: list[AuditTimelineEvent] = [
            timeline_event(
                run.created_at,
                "analysis_run_created",
                "analysis_run",
                run.id,
                "Analysis run created",
                f"Analysis run entered {run.status} status.",
                metadata=self.analysis_run_metadata(run),
                include_metadata=resolved_options.include_metadata,
            ),
            timeline_event(
                run.start_time,
                "candle_window_resolved",
                "analysis_run",
                run.id,
                "Candle window resolved",
                "The analysis run references a bounded candle window without exposing raw candles.",
                metadata={
                    "start_time": run.start_time,
                    "end_time": run.end_time,
                    "warmup_start_time": run.warmup_start_time,
                    "baseline_start_time": run.baseline_start_time,
                    "raw_candle_series_included": False,
                },
                include_metadata=resolved_options.include_metadata,
            ),
        ]
        if run.completed_at is not None:
            events.append(
                timeline_event(
                    run.completed_at,
                    "analysis_run_completed",
                    "analysis_run",
                    run.id,
                    "Analysis run completed",
                    f"Analysis run finished with {run.status} status.",
                    severity=(
                        AuditTimelineSeverity.ERROR
                        if run.status == "failed"
                        else AuditTimelineSeverity.INFO
                    ),
                    metadata={"error_code": run.error_code, "error_message": run.error_message},
                    include_metadata=resolved_options.include_metadata,
                )
            )
        self.add_snapshot_event(
            events,
            context.feature_snapshot,
            "feature_snapshot",
            resolved_options,
        )
        self.add_snapshot_event(
            events,
            context.indicator_snapshot,
            "indicator_snapshot",
            resolved_options,
        )
        self.add_pattern_events(events, context.pattern_candidates, resolved_options)
        if context.signal is not None:
            self.add_signal_event(events, context.signal, resolved_options)
            self.add_signal_detail_events(
                events,
                context.signal,
                context.evidence,
                context.confidence_components,
                context.risk_notes,
                resolved_options,
            )
        self.add_explanation_events(
            events,
            context.deterministic_explanation,
            context.llm_explanations,
            resolved_options,
        )
        await self.add_news_events(events, context.news_correlations, resolved_options)
        self.add_outcome_events(events, context.outcomes, resolved_options)
        self.add_reasoning_events(events, context.reasoning_runs, resolved_options)
        self.add_action_plan_events(events, context.action_plans, [], resolved_options)
        self.add_replay_events(events, context.replay_runs, resolved_options)
        self.add_chart_events(events, context.chart_runs, resolved_options)
        self.add_scheduled_scan_events(
            events,
            context.scan_items,
            context.scan_runs,
            resolved_options,
        )
        self.add_quality_events(
            events,
            context.quality_runs,
            context.quality_findings,
            context.shadow_results,
            resolved_options,
        )
        self.add_audit_events(events, context.audit_logs, resolved_options)
        graph = self.analysis_graph(run, context, resolved_options.include_graph)
        completeness = completeness_from_components(
            {
                "analysis_run": True,
                "candle_window": True,
                "feature_snapshot": context.feature_snapshot is not None,
                "indicator_snapshot": context.indicator_snapshot is not None,
                "pattern_candidates": bool(context.pattern_candidates),
                "signal": context.signal is not None,
                "signal_evidence": bool(context.evidence),
                "confidence_components": bool(context.confidence_components),
                "risk_notes": bool(context.risk_notes),
                "deterministic_explanation": context.deterministic_explanation is not None,
                "scheduled_scan_provenance": bool(context.scan_items),
                "quality_runs": bool(context.quality_runs),
                "audit_logs": bool(context.audit_logs),
            }
        )
        return self.timeline_response(
            subject_type=(
                AuditTimelineSubjectType.REPLAY
                if run.analysis_mode == "replay"
                else AuditTimelineSubjectType.ANALYSIS_RUN
            ),
            subject_id=run.id,
            workspace_id=run.workspace_id,
            completeness=completeness,
            events=events,
            graph=graph,
            sections=self.analysis_sections(context, resolved_options),
            options=resolved_options,
        )

    async def build_signal_timeline(
        self,
        signal_id: UUID,
        options: AuditTimelineOptions | None = None,
    ) -> AuditTimelineRead:
        resolved_options = options or AuditTimelineOptions()
        signal = await self.repository.get_signal(signal_id)
        if signal is None:
            raise AppError(404, "signal_not_found", "Signal not found")
        run = await self.repository.get_analysis_run(signal.analysis_run_id)
        if run is None:
            raise AppError(404, "analysis_run_not_found", "Parent analysis run not found")
        context = await self.analysis_context(run, resolved_options, signal)
        selected_candidate = (
            await self.repository.get_pattern_candidate(signal.selected_pattern_candidate_id)
            if signal.selected_pattern_candidate_id is not None
            else None
        )
        diagnostics = await self.signal_diagnostics(signal, resolved_options)
        events: list[AuditTimelineEvent] = []
        events.append(
            timeline_event(
                signal.created_at,
                "signal_classified",
                "signal",
                signal.id,
                "Signal classified",
                f"Deterministic classifier persisted {signal.classification_status}.",
                metadata=self.signal_metadata(signal),
                include_metadata=resolved_options.include_metadata,
            )
        )
        if run is not None:
            events.append(
                timeline_event(
                    run.created_at,
                    "parent_analysis_run_created",
                    "analysis_run",
                    run.id,
                    "Parent analysis run created",
                    "The signal is linked to this analysis run.",
                    metadata=self.analysis_run_metadata(run),
                    include_metadata=resolved_options.include_metadata,
                )
            )
        if selected_candidate is not None:
            self.add_pattern_events(events, [selected_candidate], resolved_options)
        self.add_signal_detail_events(
            events,
            signal,
            context.evidence,
            context.confidence_components,
            context.risk_notes,
            resolved_options,
        )
        self.add_explanation_events(
            events,
            context.deterministic_explanation,
            context.llm_explanations,
            resolved_options,
        )
        await self.add_news_events(events, context.news_correlations, resolved_options)
        self.add_reasoning_events(events, context.reasoning_runs, resolved_options)
        self.add_action_plan_events(events, context.action_plans, [], resolved_options)
        self.add_outcome_events(events, context.outcomes, resolved_options)
        self.add_chart_events(events, context.chart_runs, resolved_options)
        self.add_scheduled_scan_events(
            events,
            context.scan_items,
            context.scan_runs,
            resolved_options,
        )
        self.add_quality_events(
            events,
            diagnostics["quality_runs"],
            diagnostics["quality_findings"],
            diagnostics["shadow_results"],
            resolved_options,
        )
        self.add_audit_events(events, context.audit_logs, resolved_options)
        graph = self.signal_graph(
            signal,
            context,
            selected_candidate,
            resolved_options.include_graph,
        )
        completeness = completeness_from_components(
            {
                "analysis_run": run is not None,
                "strategy_profile_snapshot": signal.strategy_profile_snapshot_json is not None,
                "selected_pattern_candidate": selected_candidate is not None,
                "signal_evidence": bool(context.evidence),
                "confidence_components": bool(context.confidence_components),
                "risk_notes": bool(context.risk_notes),
                "deterministic_explanation": context.deterministic_explanation is not None,
                "outcomes": bool(context.outcomes),
                "scheduled_scan_provenance": bool(context.scan_items),
                "quality_runs": bool(diagnostics["quality_runs"]),
                "audit_logs": bool(context.audit_logs),
            }
        )
        sections = self.signal_sections(
            signal,
            context,
            selected_candidate,
            diagnostics,
            resolved_options,
        )
        return self.timeline_response(
            subject_type=AuditTimelineSubjectType.SIGNAL,
            subject_id=signal.id,
            workspace_id=signal.workspace_id,
            completeness=completeness,
            events=events,
            graph=graph,
            sections=sections,
            options=resolved_options,
        )

    async def build_reasoning_run_timeline(
        self,
        reasoning_run_id: UUID,
        options: AuditTimelineOptions | None = None,
    ) -> AuditTimelineRead:
        resolved_options = options or AuditTimelineOptions()
        run = await self.repository.get_reasoning_run(reasoning_run_id)
        if run is None:
            raise AppError(404, "reasoning_run_not_found", "Reasoning run not found")
        scenarios = await self.repository.list_scenario_hypotheses(
            run.id,
            resolved_options.limit_artifacts,
        )
        plans = await self.repository.list_action_plans_by_reasoning_run_id(
            run.id,
            resolved_options.limit_artifacts,
        )
        audit_logs = (
            await self.repository.list_audit_logs(run.analysis_run_id, resolved_options.limit_audit)
            if resolved_options.include_audit and run.analysis_run_id is not None
            else []
        )
        events = [
            timeline_event(
                run.created_at,
                "reasoning_input_built",
                "reasoning_run",
                run.id,
                "Reasoning input built",
                "Scenario reasoning was created from persisted backend artifacts.",
                metadata={
                    "source_type": run.source_type,
                    "reasoning_type": run.reasoning_type,
                    "input_snapshot": run.input_snapshot_json,
                },
                include_metadata=resolved_options.include_metadata,
            ),
            timeline_event(
                run.created_at,
                "reasoning_provider_selected",
                "reasoning_run",
                run.id,
                "Reasoning provider selected",
                f"Provider {run.provider} and model {run.model} were recorded.",
                metadata={
                    "provider": run.provider,
                    "model": run.model,
                    "prompt_version": run.prompt_version,
                    "tokens_input": run.tokens_input,
                    "tokens_output": run.tokens_output,
                    "estimated_cost": run.estimated_cost,
                },
                include_metadata=resolved_options.include_metadata,
            ),
            timeline_event(
                run.updated_at,
                "reasoning_safety_grounding_checked",
                "reasoning_run",
                run.id,
                "Safety and grounding checked",
                f"Safety={run.safety_status}; grounding={run.grounding_status}.",
                severity=self.status_severity(run.status),
                metadata={
                    "status": run.status,
                    "safety_status": run.safety_status,
                    "grounding_status": run.grounding_status,
                    "blocked_terms": run.blocked_terms_json,
                    "grounding_issues": run.grounding_issues_json,
                    "error_message": run.error_message,
                },
                include_metadata=resolved_options.include_metadata,
            ),
        ]
        self.add_scenario_events(events, scenarios, resolved_options)
        self.add_action_plan_events(events, plans, [], resolved_options)
        self.add_audit_events(events, audit_logs, resolved_options)
        graph = self.reasoning_graph(run, scenarios, plans, resolved_options.include_graph)
        completeness = completeness_from_components(
            {
                "reasoning_run": True,
                "input_snapshot": bool(run.input_snapshot_json),
                "provider_model": bool(run.provider and run.model),
                "safety_status": bool(run.safety_status),
                "grounding_status": bool(run.grounding_status),
                "scenario_hypotheses": bool(scenarios),
                "action_plan": bool(plans),
            }
        )
        return self.timeline_response(
            subject_type=AuditTimelineSubjectType.REASONING_RUN,
            subject_id=run.id,
            workspace_id=run.workspace_id,
            completeness=completeness,
            events=events,
            graph=graph,
            sections=self.reasoning_sections(run, scenarios, plans, resolved_options),
            options=resolved_options,
        )

    async def build_action_plan_timeline(
        self,
        action_plan_id: UUID,
        options: AuditTimelineOptions | None = None,
    ) -> AuditTimelineRead:
        resolved_options = options or AuditTimelineOptions()
        plan = await self.repository.get_action_plan(action_plan_id)
        if plan is None:
            raise AppError(404, "action_plan_not_found", "Action plan not found")
        items = await self.repository.list_action_items(plan.id, resolved_options.limit_artifacts)
        worker_runs = await self.repository.list_optional_action_worker_runs(
            plan.workspace_id,
            min(resolved_options.limit_artifacts, 25),
        )
        events = [
            timeline_event(
                plan.created_at,
                "action_plan_created",
                "action_plan",
                plan.id,
                "Action plan created",
                "Backend-safe follow-up items were planned without executing trading actions.",
                metadata=self.action_plan_metadata(plan),
                include_metadata=resolved_options.include_metadata,
            )
        ]
        self.add_action_item_events(events, items, resolved_options)
        for worker_run in worker_runs:
            event_time = worker_run.get("created_at")
            if isinstance(event_time, datetime):
                events.append(
                    timeline_event(
                        event_time,
                        "action_worker_run_recorded",
                        "reasoning_action_worker_run",
                        str(worker_run.get("id")),
                        "Action worker run recorded",
                        f"Worker run status was {worker_run.get('status')}.",
                        severity=(
                            AuditTimelineSeverity.ERROR
                            if worker_run.get("status") == "failed"
                            else AuditTimelineSeverity.INFO
                        ),
                        metadata=worker_run,
                        include_metadata=resolved_options.include_metadata,
                    )
                )
        graph = self.action_plan_graph(plan, items, resolved_options.include_graph)
        completeness = completeness_from_components(
            {
                "action_plan": True,
                "action_items": bool(items),
                "rejected_actions_metadata": bool(plan.metadata_json.get("rejectedActions")),
                "worker_runs": bool(worker_runs),
                "completed_or_terminal_items": any(
                    item.status in {"completed", "skipped", "failed", "cancelled"} for item in items
                ),
            }
        )
        return self.timeline_response(
            subject_type=AuditTimelineSubjectType.ACTION_PLAN,
            subject_id=plan.id,
            workspace_id=plan.workspace_id,
            completeness=completeness,
            events=events,
            graph=graph,
            sections=self.action_plan_sections(plan, items, worker_runs, resolved_options),
            options=resolved_options,
        )

    async def build_outcome_timeline(
        self,
        outcome_id: UUID,
        options: AuditTimelineOptions | None = None,
    ) -> AuditTimelineRead:
        resolved_options = options or AuditTimelineOptions()
        outcome = await self.repository.get_outcome(outcome_id)
        if outcome is None:
            raise AppError(404, "outcome_not_found", "Outcome not found")
        signal = await self.repository.get_signal(outcome.signal_id)
        run = await self.repository.get_analysis_run(outcome.analysis_run_id)
        reasoning_runs = await self.repository.list_reasoning_runs_by_outcome_id(
            outcome.id,
            resolved_options.limit_artifacts,
        )
        action_items = await self.repository.list_action_items_by_signal_id(
            outcome.signal_id,
            resolved_options.limit_artifacts,
        )
        diagnostics = await self.outcome_diagnostics(outcome, resolved_options)
        audit_logs = (
            await self.repository.list_audit_logs(
                outcome.analysis_run_id,
                resolved_options.limit_audit,
            )
            if resolved_options.include_audit
            else []
        )
        events = [
            timeline_event(
                outcome.created_at,
                "outcome_evaluated",
                "outcome",
                outcome.id,
                "Outcome evaluated",
                f"Outcome label was {outcome.outcome_label}.",
                severity=self.status_severity(outcome.evaluation_status),
                metadata=self.outcome_metadata(outcome),
                include_metadata=resolved_options.include_metadata,
            )
        ]
        if signal is not None:
            self.add_signal_event(events, signal, resolved_options)
        if run is not None:
            events.append(
                timeline_event(
                    run.created_at,
                    "parent_analysis_run_created",
                    "analysis_run",
                    run.id,
                    "Parent analysis run created",
                    "Outcome is linked to this analysis run.",
                    metadata=self.analysis_run_metadata(run),
                    include_metadata=resolved_options.include_metadata,
                )
            )
        self.add_reasoning_events(events, reasoning_runs, resolved_options)
        self.add_action_item_events(events, action_items, resolved_options)
        self.add_audit_events(events, audit_logs, resolved_options)
        graph = self.outcome_graph(
            outcome,
            signal,
            run,
            reasoning_runs,
            action_items,
            resolved_options.include_graph,
        )
        completeness = completeness_from_components(
            {
                "outcome": True,
                "parent_signal": signal is not None,
                "parent_analysis_run": run is not None,
                "reference_window": bool(outcome.future_window_start and outcome.future_window_end),
                "movement_stats": outcome.net_move is not None,
                "evaluation_status": bool(outcome.evaluation_status),
                "diagnostics": any(diagnostics.values()),
                "linked_action_items": bool(action_items),
            }
        )
        return self.timeline_response(
            subject_type=AuditTimelineSubjectType.OUTCOME,
            subject_id=outcome.id,
            workspace_id=outcome.workspace_id,
            completeness=completeness,
            events=events,
            graph=graph,
            sections=self.outcome_sections(
                outcome,
                signal,
                run,
                reasoning_runs,
                action_items,
                diagnostics,
                resolved_options,
            ),
            options=resolved_options,
        )

    async def build_chart_screenshot_run_timeline(
        self,
        run_id: UUID,
        options: AuditTimelineOptions | None = None,
    ) -> AuditTimelineRead:
        resolved_options = options or AuditTimelineOptions()
        run = await self.repository.get_chart_screenshot_run(run_id)
        if run is None:
            raise AppError(
                404,
                "chart_screenshot_run_not_found",
                "Chart screenshot run not found",
            )
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
        quality_runs = (
            await self.repository.list_quality_runs_by_analysis_run_id(
                analysis_run.id,
                resolved_options.limit_artifacts,
            )
            if analysis_run is not None
            else []
        )
        quality_run_ids = [item.id for item in quality_runs]
        quality_findings = await self.repository.list_quality_findings_by_run_ids(
            quality_run_ids,
            resolved_options.limit_artifacts,
        )
        shadow_results = await self.repository.list_shadow_results_by_quality_run_ids(
            quality_run_ids,
            resolved_options.limit_artifacts,
        )
        corrections = await self.repository.list_chart_corrections(
            run.id,
            resolved_options.limit_artifacts,
        )
        audit_logs = (
            await self.repository.list_audit_logs(analysis_run.id, resolved_options.limit_audit)
            if resolved_options.include_audit and analysis_run is not None
            else []
        )
        events = [
            timeline_event(
                run.created_at,
                "chart_screenshot_run_created",
                "chart_screenshot_run",
                run.id,
                "Screenshot run created",
                f"Screenshot parser {run.parser_name} recorded status {run.status}.",
                metadata=self.chart_screenshot_metadata(run),
                include_metadata=resolved_options.include_metadata,
            )
        ]
        if run.started_at is not None:
            events.append(
                timeline_event(
                    run.started_at,
                    "chart_screenshot_parsing_started",
                    "chart_screenshot_run",
                    run.id,
                    "Screenshot parsing started",
                    "The stored screenshot run entered parsing.",
                    metadata={"parser_version": run.parser_version},
                    include_metadata=resolved_options.include_metadata,
                )
            )
        if run.completed_at is not None:
            events.append(
                timeline_event(
                    run.completed_at,
                    "chart_screenshot_run_completed",
                    "chart_screenshot_run",
                    run.id,
                    "Screenshot run completed",
                    f"Extraction confidence was {run.extraction_confidence}.",
                    severity=self.status_severity(run.status),
                    metadata={
                        "raw_candle_count": run.raw_candle_count,
                        "stored_candle_count": run.stored_candle_count,
                        "duplicate_count": run.duplicate_count,
                        "conflict_count": run.conflict_count,
                    },
                    include_metadata=resolved_options.include_metadata,
                )
            )
        review = self.human_review(run)
        if review is not None:
            events.append(
                timeline_event(
                    run.updated_at,
                    "chart_screenshot_human_review_recorded",
                    "chart_screenshot_run",
                    run.id,
                    "Human review recorded",
                    f"Human review status is {review.get('status', 'recorded')}.",
                    metadata=review,
                    include_metadata=resolved_options.include_metadata,
                )
            )
        self.add_chart_events(
            events,
            corrections,
            resolved_options,
            event_type="chart_correction_created",
        )
        if analysis_run is not None:
            events.append(
                timeline_event(
                    analysis_run.created_at,
                    "linked_analysis_run_created",
                    "analysis_run",
                    analysis_run.id,
                    "Linked analysis run created",
                    "The screenshot run is linked to an existing analysis run.",
                    metadata=self.analysis_run_metadata(analysis_run),
                    include_metadata=resolved_options.include_metadata,
                )
            )
        if signal is not None:
            self.add_signal_event(events, signal, resolved_options)
        self.add_quality_events(
            events,
            quality_runs,
            quality_findings,
            shadow_results,
            resolved_options,
        )
        self.add_audit_events(events, audit_logs, resolved_options)
        graph = self.chart_graph(
            run,
            analysis_run,
            signal,
            corrections,
            resolved_options.include_graph,
        )
        completeness = completeness_from_components(
            {
                "chart_screenshot_run": True,
                "parser_metadata": bool(run.parser_metadata_json),
                "extracted_payload": run.extracted_payload_json is not None,
                "extraction_confidence": run.extraction_confidence is not None,
                "linked_analysis_run": analysis_run is not None,
                "human_review": review is not None,
                "corrections": bool(corrections),
                "quality_runs": bool(quality_runs),
                "audit_logs": bool(audit_logs),
            }
        )
        return self.timeline_response(
            subject_type=AuditTimelineSubjectType.CHART_SCREENSHOT_RUN,
            subject_id=run.id,
            workspace_id=run.workspace_id,
            completeness=completeness,
            events=events,
            graph=graph,
            sections=self.chart_sections(
                run,
                analysis_run,
                signal,
                corrections,
                quality_runs,
                quality_findings,
                shadow_results,
                resolved_options,
            ),
            options=resolved_options,
        )

    async def analysis_context(
        self,
        run: AnalysisRun,
        options: AuditTimelineOptions,
        signal: Signal | None = None,
    ) -> "AnalysisTimelineContext":
        resolved_signal = signal or await self.repository.get_signal_by_analysis_run_id(run.id)
        evidence: list[SignalEvidence] = []
        confidence_components: list[SignalConfidenceComponent] = []
        risk_notes: list[SignalRiskNote] = []
        deterministic_explanation: DeterministicExplanation | None = None
        llm_explanations: list[LlmExplanation] = []
        news_correlations: list[SignalNewsCorrelation] = []
        reasoning_runs: list[LlmReasoningRun] = []
        action_plans: list[ReasoningActionPlan] = []
        outcomes: list[SignalOutcome] = []
        scan_items = await self.repository.list_scheduled_scan_items_by_analysis_run_id(
            run.id,
            options.limit_artifacts,
        )
        scan_runs = await self.repository.list_scheduled_scan_runs_by_item_ids(
            self.scan_run_ids(scan_items),
            options.limit_artifacts,
        )
        quality_runs = await self.repository.list_quality_runs_by_analysis_run_id(
            run.id,
            options.limit_artifacts,
        )
        if resolved_signal is not None:
            quality_runs = self.dedupe_artifacts(
                quality_runs
                + await self.repository.list_quality_runs_by_signal_id(
                    resolved_signal.id,
                    options.limit_artifacts,
                )
            )
        quality_run_ids = [item.id for item in quality_runs]
        quality_findings = await self.repository.list_quality_findings_by_run_ids(
            quality_run_ids,
            options.limit_artifacts,
        )
        shadow_results = await self.repository.list_shadow_results_by_quality_run_ids(
            quality_run_ids,
            options.limit_artifacts,
        )
        if resolved_signal is not None:
            evidence = await self.repository.list_evidence(
                resolved_signal.id,
                options.limit_artifacts,
            )
            confidence_components = await self.repository.list_confidence_components(
                resolved_signal.id,
                options.limit_artifacts,
            )
            risk_notes = await self.repository.list_risk_notes(
                resolved_signal.id,
                options.limit_artifacts,
            )
            deterministic_explanation = (
                await self.repository.get_deterministic_explanation_by_signal_id(resolved_signal.id)
            )
            llm_explanations = await self.repository.list_llm_explanations_by_signal_id(
                resolved_signal.id,
                options.limit_artifacts,
            )
            news_correlations = await self.repository.list_news_correlations_by_signal_id(
                resolved_signal.id,
                options.limit_artifacts,
            )
            reasoning_runs = await self.repository.list_reasoning_runs_by_signal_id(
                resolved_signal.id,
                options.limit_artifacts,
            )
            reasoning_runs = self.dedupe_artifacts(
                reasoning_runs
                + await self.repository.list_reasoning_runs_by_analysis_run_id(
                    run.id,
                    options.limit_artifacts,
                )
            )
            action_plans = await self.repository.list_action_plans_by_signal_id(
                resolved_signal.id,
                options.limit_artifacts,
            )
            action_plans = self.dedupe_artifacts(
                action_plans
                + await self.repository.list_action_plans_by_analysis_run_id(
                    run.id,
                    options.limit_artifacts,
                )
            )
            outcomes = await self.repository.list_signal_outcomes(
                resolved_signal.id,
                options.limit_artifacts,
            )
        else:
            deterministic_explanation = (
                await self.repository.get_deterministic_explanation_by_analysis_run_id(run.id)
            )
            llm_explanations = await self.repository.list_llm_explanations_by_analysis_run_id(
                run.id,
                options.limit_artifacts,
            )
            news_correlations = await self.repository.list_news_correlations_by_analysis_run_id(
                run.id,
                options.limit_artifacts,
            )
            reasoning_runs = await self.repository.list_reasoning_runs_by_analysis_run_id(
                run.id,
                options.limit_artifacts,
            )
            action_plans = await self.repository.list_action_plans_by_analysis_run_id(
                run.id,
                options.limit_artifacts,
            )
            outcomes = await self.repository.list_analysis_outcomes(
                run.id,
                options.limit_artifacts,
            )
        return AnalysisTimelineContext(
            run=run,
            signal=resolved_signal,
            feature_snapshot=await self.repository.get_feature_snapshot(run.id),
            indicator_snapshot=await self.repository.get_indicator_snapshot(run.id),
            pattern_candidates=await self.repository.list_pattern_candidates(
                run.id,
                options.limit_artifacts,
            ),
            evidence=evidence,
            confidence_components=confidence_components,
            risk_notes=risk_notes,
            deterministic_explanation=deterministic_explanation,
            llm_explanations=llm_explanations,
            news_correlations=news_correlations,
            outcomes=outcomes,
            reasoning_runs=reasoning_runs,
            action_plans=action_plans,
            replay_runs=await self.repository.list_replay_runs(run.id, options.limit_artifacts),
            chart_runs=await self.repository.list_chart_screenshot_runs_by_analysis_run_id(
                run.id,
                options.limit_artifacts,
            ),
            scan_items=scan_items,
            scan_runs=scan_runs,
            quality_runs=quality_runs,
            quality_findings=quality_findings,
            shadow_results=shadow_results,
            audit_logs=(
                await self.repository.list_audit_logs(run.id, options.limit_audit)
                if options.include_audit
                else []
            ),
        )

    def dedupe_artifacts(self, items: list[Any]) -> list[Any]:
        result: list[Any] = []
        seen: set[UUID] = set()
        for item in items:
            item_id = getattr(item, "id", None)
            if not isinstance(item_id, UUID) or item_id in seen:
                continue
            seen.add(item_id)
            result.append(item)
        return result

    async def signal_diagnostics(
        self,
        signal: Signal,
        options: AuditTimelineOptions,
    ) -> dict[str, list[Any]]:
        limit = min(options.limit_artifacts, 50)
        quality_runs = await self.repository.list_quality_runs_by_signal_id(signal.id, limit)
        quality_run_ids = [item.id for item in quality_runs]
        return {
            "profile_diagnostics": await self.repository.list_optional_strategy_profile_diagnostics(
                signal.workspace_id,
                signal.strategy_profile_key,
                signal.symbol_id,
                signal.timeframe,
                limit,
            ),
            "pattern_diagnostics": await self.repository.list_optional_pattern_diagnostics(
                signal.workspace_id,
                signal.pattern_type,
                signal.strategy_profile_key,
                signal.symbol_id,
                signal.timeframe,
                limit,
            ),
            "calibration_recommendations": (
                await self.repository.list_optional_calibration_recommendations(
                    signal.workspace_id,
                    signal.strategy_profile_key,
                    signal.pattern_type,
                    signal.symbol_id,
                    signal.timeframe,
                    limit,
                )
            ),
            "quality_runs": quality_runs,
            "quality_findings": await self.repository.list_quality_findings_by_run_ids(
                quality_run_ids,
                limit,
            ),
            "shadow_results": await self.repository.list_shadow_results_by_quality_run_ids(
                quality_run_ids,
                limit,
            ),
        }

    def scan_run_ids(self, items: list[ScheduledScanRunItem]) -> list[UUID]:
        result: list[UUID] = []
        seen: set[UUID] = set()
        for item in items:
            if item.scan_run_id in seen:
                continue
            seen.add(item.scan_run_id)
            result.append(item.scan_run_id)
        return result

    async def outcome_diagnostics(
        self,
        outcome: SignalOutcome,
        options: AuditTimelineOptions,
    ) -> dict[str, list[dict[str, Any]]]:
        limit = min(options.limit_artifacts, 50)
        return {
            "profile_diagnostics": await self.repository.list_optional_strategy_profile_diagnostics(
                outcome.workspace_id,
                outcome.strategy_profile_key,
                outcome.symbol_id,
                outcome.timeframe,
                limit,
            ),
            "pattern_diagnostics": await self.repository.list_optional_pattern_diagnostics(
                outcome.workspace_id,
                outcome.pattern_type,
                outcome.strategy_profile_key,
                outcome.symbol_id,
                outcome.timeframe,
                limit,
            ),
            "calibration_recommendations": (
                await self.repository.list_optional_calibration_recommendations(
                    outcome.workspace_id,
                    outcome.strategy_profile_key,
                    outcome.pattern_type,
                    outcome.symbol_id,
                    outcome.timeframe,
                    limit,
                )
            ),
        }

    def timeline_response(
        self,
        subject_type: AuditTimelineSubjectType,
        subject_id: UUID,
        workspace_id: UUID,
        completeness: AuditTimelineCompleteness,
        events: list[AuditTimelineEvent],
        graph: ArtifactGraph,
        sections: dict[str, Any],
        options: AuditTimelineOptions,
    ) -> AuditTimelineRead:
        safe_sections = to_timeline_value(sections) if options.include_artifacts else {}
        warnings = [
            "Audit timelines are read-only traceability views over persisted artifacts.",
            "Completeness measures traceability coverage only, not quality or profitability.",
        ]
        return AuditTimelineRead(
            subject=AuditTimelineSubject(type=subject_type, id=subject_id),
            workspace_id=workspace_id,
            generated_at=utc_now(),
            completeness=completeness,
            timeline=bounded_timeline(events, options.limit_events),
            artifact_graph=graph,
            sections=safe_sections if isinstance(safe_sections, dict) else {},
            warnings=warnings,
        )

    def add_snapshot_event(
        self,
        events: list[AuditTimelineEvent],
        snapshot: FeatureSnapshot | IndicatorSnapshot | None,
        source_type: str,
        options: AuditTimelineOptions,
    ) -> None:
        if snapshot is None:
            return
        field_name = "features_json" if source_type == "feature_snapshot" else "indicators_json"
        events.append(
            timeline_event(
                snapshot.created_at,
                f"{source_type}_created",
                source_type,
                snapshot.id,
                source_type.replace("_", " ").title(),
                f"{source_type.replace('_', ' ')} was persisted.",
                metadata={"keys": sorted(getattr(snapshot, field_name).keys())[:50]},
                include_metadata=options.include_metadata,
            )
        )

    def add_pattern_events(
        self,
        events: list[AuditTimelineEvent],
        candidates: list[PatternCandidate],
        options: AuditTimelineOptions,
    ) -> None:
        for candidate in candidates:
            events.append(
                timeline_event(
                    candidate.created_at,
                    "pattern_candidate_created",
                    "pattern_candidate",
                    candidate.id,
                    "Pattern candidate created",
                    f"Pattern candidate {candidate.pattern_type} was persisted.",
                    metadata={
                        "pattern_type": candidate.pattern_type,
                        "bias": candidate.bias,
                        "strength_score": candidate.strength_score,
                        "is_selected": candidate.is_selected,
                    },
                    include_metadata=options.include_metadata,
                )
            )

    def add_signal_event(
        self,
        events: list[AuditTimelineEvent],
        signal: Signal,
        options: AuditTimelineOptions,
    ) -> None:
        events.append(
            timeline_event(
                signal.created_at,
                "signal_classified",
                "signal",
                signal.id,
                "Signal classified",
                f"Signal classification status is {signal.classification_status}.",
                metadata=self.signal_metadata(signal),
                include_metadata=options.include_metadata,
            )
        )

    def add_signal_detail_events(
        self,
        events: list[AuditTimelineEvent],
        signal: Signal,
        evidence: list[SignalEvidence],
        confidence_components: list[SignalConfidenceComponent],
        risk_notes: list[SignalRiskNote],
        options: AuditTimelineOptions,
    ) -> None:
        if evidence:
            events.append(
                timeline_event(
                    evidence[0].created_at,
                    "signal_evidence_persisted",
                    "signal",
                    signal.id,
                    "Signal evidence persisted",
                    f"{len(evidence)} evidence rows were linked to the signal.",
                    metadata={"evidence_count": len(evidence)},
                    include_metadata=options.include_metadata,
                )
            )
        if confidence_components:
            events.append(
                timeline_event(
                    confidence_components[0].created_at,
                    "signal_confidence_persisted",
                    "signal",
                    signal.id,
                    "Signal confidence persisted",
                    f"{len(confidence_components)} confidence components were stored.",
                    metadata={"component_count": len(confidence_components)},
                    include_metadata=options.include_metadata,
                )
            )
        if risk_notes:
            events.append(
                timeline_event(
                    risk_notes[0].created_at,
                    "signal_risk_notes_persisted",
                    "signal",
                    signal.id,
                    "Signal risk notes persisted",
                    f"{len(risk_notes)} risk notes were stored.",
                    severity=AuditTimelineSeverity.WARNING,
                    metadata={"risk_note_count": len(risk_notes)},
                    include_metadata=options.include_metadata,
                )
            )

    def add_explanation_events(
        self,
        events: list[AuditTimelineEvent],
        deterministic_explanation: DeterministicExplanation | None,
        llm_explanations: list[LlmExplanation],
        options: AuditTimelineOptions,
    ) -> None:
        if deterministic_explanation is not None:
            events.append(
                timeline_event(
                    deterministic_explanation.created_at,
                    "deterministic_explanation_generated",
                    "deterministic_explanation",
                    deterministic_explanation.id,
                    "Deterministic explanation generated",
                    (
                        f"Template {deterministic_explanation.template_version} produced "
                        "a bounded explanation."
                    ),
                    severity=self.status_severity(deterministic_explanation.safety_status),
                    metadata={
                        "signal_id": deterministic_explanation.signal_id,
                        "analysis_run_id": deterministic_explanation.analysis_run_id,
                        "safety_status": deterministic_explanation.safety_status,
                    },
                    include_metadata=options.include_metadata,
                )
            )
        for explanation in llm_explanations:
            events.append(
                timeline_event(
                    explanation.created_at,
                    "llm_explanation_generated",
                    "llm_explanation",
                    explanation.id,
                    "LLM explanation generated",
                    f"Optional LLM explanation recorded safety={explanation.safety_status}.",
                    severity=self.status_severity(explanation.safety_status),
                    metadata={
                        "provider": explanation.provider,
                        "model": explanation.model,
                        "prompt_version": explanation.prompt_version,
                        "grounding_status": explanation.grounding_status,
                    },
                    include_metadata=options.include_metadata,
                )
            )

    async def add_news_events(
        self,
        events: list[AuditTimelineEvent],
        correlations: list[SignalNewsCorrelation],
        options: AuditTimelineOptions,
    ) -> None:
        news_events = {
            event.id: event
            for event in await self.repository.list_news_events(
                [correlation.news_event_id for correlation in correlations]
            )
        }
        for correlation in correlations:
            news_event = news_events.get(correlation.news_event_id)
            events.append(
                timeline_event(
                    correlation.created_at,
                    "news_correlation_generated",
                    "signal_news_correlation",
                    correlation.id,
                    "News correlation generated",
                    f"Contextual correlation label is {correlation.correlation_label}.",
                    metadata={
                        "news_event_id": correlation.news_event_id,
                        "news_event_title": news_event.title if news_event is not None else None,
                        "correlation_score": correlation.correlation_score,
                        "direction_alignment": correlation.direction_alignment,
                        "volatility_reaction": correlation.volatility_reaction,
                    },
                    include_metadata=options.include_metadata,
                )
            )

    def add_outcome_events(
        self,
        events: list[AuditTimelineEvent],
        outcomes: list[SignalOutcome],
        options: AuditTimelineOptions,
    ) -> None:
        for outcome in outcomes:
            events.append(
                timeline_event(
                    outcome.created_at,
                    "outcome_evaluated",
                    "outcome",
                    outcome.id,
                    "Outcome evaluated",
                    f"{outcome.horizon_minutes} minute outcome is {outcome.outcome_label}.",
                    severity=self.status_severity(outcome.evaluation_status),
                    metadata=self.outcome_metadata(outcome),
                    include_metadata=options.include_metadata,
                )
            )

    def add_reasoning_events(
        self,
        events: list[AuditTimelineEvent],
        reasoning_runs: list[LlmReasoningRun],
        options: AuditTimelineOptions,
    ) -> None:
        for run in reasoning_runs:
            events.append(
                timeline_event(
                    run.created_at,
                    "reasoning_run_created",
                    "reasoning_run",
                    run.id,
                    "Reasoning run created",
                    f"Reasoning run status is {run.status}.",
                    severity=self.status_severity(run.status),
                    metadata={
                        "source_type": run.source_type,
                        "provider": run.provider,
                        "model": run.model,
                        "reasoning_type": run.reasoning_type,
                        "safety_status": run.safety_status,
                        "grounding_status": run.grounding_status,
                    },
                    include_metadata=options.include_metadata,
                )
            )

    def add_scenario_events(
        self,
        events: list[AuditTimelineEvent],
        scenarios: list[ScenarioHypothesis],
        options: AuditTimelineOptions,
    ) -> None:
        for scenario in scenarios:
            events.append(
                timeline_event(
                    scenario.created_at,
                    "scenario_hypothesis_persisted",
                    "scenario_hypothesis",
                    scenario.id,
                    "Scenario hypothesis persisted",
                    f"Scenario type is {scenario.scenario_type}.",
                    metadata={
                        "scenario_type": scenario.scenario_type,
                        "possibility_label": scenario.possibility_label,
                        "suggested_backend_actions": scenario.suggested_backend_actions_json,
                    },
                    include_metadata=options.include_metadata,
                )
            )

    def add_action_plan_events(
        self,
        events: list[AuditTimelineEvent],
        plans: list[ReasoningActionPlan],
        items: list[ReasoningActionItem],
        options: AuditTimelineOptions,
    ) -> None:
        for plan in plans:
            events.append(
                timeline_event(
                    plan.created_at,
                    "action_plan_created",
                    "action_plan",
                    plan.id,
                    "Action plan created",
                    f"Action plan status is {plan.status}.",
                    metadata=self.action_plan_metadata(plan),
                    include_metadata=options.include_metadata,
                )
            )
        self.add_action_item_events(events, items, options)

    def add_action_item_events(
        self,
        events: list[AuditTimelineEvent],
        items: list[ReasoningActionItem],
        options: AuditTimelineOptions,
    ) -> None:
        for item in items:
            events.append(
                timeline_event(
                    item.created_at,
                    "action_item_created",
                    "action_item",
                    item.id,
                    "Action item created",
                    f"Backend-safe action item {item.action_type} is {item.status}.",
                    severity=self.status_severity(item.status),
                    metadata=self.action_item_metadata(item),
                    include_metadata=options.include_metadata,
                )
            )
            if item.last_attempted_at is not None:
                events.append(
                    timeline_event(
                        item.last_attempted_at,
                        "action_item_attempted",
                        "action_item",
                        item.id,
                        "Action item attempted",
                        f"Action item attempt count is {item.attempts}.",
                        severity=self.status_severity(item.status),
                        metadata=self.action_item_metadata(item),
                        include_metadata=options.include_metadata,
                    )
                )
            if item.completed_at is not None:
                events.append(
                    timeline_event(
                        item.completed_at,
                        "action_item_completed",
                        "action_item",
                        item.id,
                        "Action item completed",
                        f"Action item completed with status {item.status}.",
                        severity=self.status_severity(item.status),
                        metadata=self.action_item_metadata(item),
                        include_metadata=options.include_metadata,
                    )
                )

    def add_replay_events(
        self,
        events: list[AuditTimelineEvent],
        replay_runs: list[AnalysisRun],
        options: AuditTimelineOptions,
    ) -> None:
        for run in replay_runs:
            events.append(
                timeline_event(
                    run.created_at,
                    "replay_run_created",
                    "analysis_run",
                    run.id,
                    "Replay run created",
                    f"Replay run status is {run.status}.",
                    metadata=self.analysis_run_metadata(run),
                    include_metadata=options.include_metadata,
                )
            )

    def add_chart_events(
        self,
        events: list[AuditTimelineEvent],
        runs: list[ChartScreenshotRun],
        options: AuditTimelineOptions,
        event_type: str = "chart_screenshot_run_linked",
    ) -> None:
        for run in runs:
            events.append(
                timeline_event(
                    run.created_at,
                    event_type,
                    "chart_screenshot_run",
                    run.id,
                    "Chart screenshot run linked",
                    f"Chart screenshot run status is {run.status}.",
                    severity=self.status_severity(run.status),
                    metadata=self.chart_screenshot_metadata(run),
                    include_metadata=options.include_metadata,
                )
            )

    def add_scheduled_scan_events(
        self,
        events: list[AuditTimelineEvent],
        items: list[ScheduledScanRunItem],
        runs: list[ScheduledScanRun],
        options: AuditTimelineOptions,
    ) -> None:
        for run in runs:
            events.append(
                timeline_event(
                    run.created_at,
                    "scheduled_scan_run_linked",
                    "scheduled_scan_run",
                    run.id,
                    "Scheduled scan run linked",
                    f"Scheduled scan run status is {run.status}.",
                    severity=self.status_severity(run.status),
                    metadata=self.scheduled_scan_run_metadata(run),
                    include_metadata=options.include_metadata,
                )
            )
        for item in items:
            events.append(
                timeline_event(
                    item.created_at,
                    "scheduled_scan_item_linked",
                    "scheduled_scan_run_item",
                    item.id,
                    "Scheduled scan item linked",
                    f"Scheduled scan item status is {item.status}.",
                    severity=self.status_severity(item.status),
                    metadata=self.scheduled_scan_item_metadata(item),
                    include_metadata=options.include_metadata,
                )
            )

    def add_quality_events(
        self,
        events: list[AuditTimelineEvent],
        runs: list[IntelligenceQualityRun],
        findings: list[IntelligenceQualityFinding],
        shadow_results: list[ShadowClassificationResult],
        options: AuditTimelineOptions,
    ) -> None:
        for run in runs:
            events.append(
                timeline_event(
                    run.created_at,
                    "intelligence_quality_run_linked",
                    "intelligence_quality_run",
                    run.id,
                    "Quality run linked",
                    f"Quality run label is {run.quality_label}.",
                    severity=self.status_severity(run.status),
                    metadata=self.quality_run_metadata(run),
                    include_metadata=options.include_metadata,
                )
            )
        for finding in findings:
            events.append(
                timeline_event(
                    finding.created_at,
                    "intelligence_quality_finding_linked",
                    "intelligence_quality_finding",
                    finding.id,
                    "Quality finding linked",
                    f"Quality finding severity is {finding.severity}.",
                    severity=self.status_severity(finding.severity),
                    metadata=self.quality_finding_metadata(finding),
                    include_metadata=options.include_metadata,
                )
            )
        for result in shadow_results:
            events.append(
                timeline_event(
                    result.created_at,
                    "shadow_classification_linked",
                    "shadow_classification_result",
                    result.id,
                    "Shadow classification linked",
                    f"Shadow agreement is {result.agreement_with_final}.",
                    severity=self.status_severity(result.agreement_with_final),
                    metadata=self.shadow_result_metadata(result),
                    include_metadata=options.include_metadata,
                )
            )

    def add_audit_events(
        self,
        events: list[AuditTimelineEvent],
        audit_logs: list[AnalysisAuditLog],
        options: AuditTimelineOptions,
    ) -> None:
        if not options.include_audit:
            return
        for log in audit_logs:
            events.append(
                timeline_event(
                    log.created_at,
                    log.event_type,
                    "analysis_audit_log",
                    log.id,
                    "Analysis audit event",
                    log.message,
                    metadata={
                        "analysis_run_id": log.analysis_run_id,
                        "metadata": log.metadata_json,
                    },
                    include_metadata=options.include_metadata,
                )
            )

    def analysis_graph(
        self,
        run: AnalysisRun,
        context: "AnalysisTimelineContext",
        include_graph: bool,
    ) -> ArtifactGraph:
        builder = ArtifactGraphBuilder()
        run_node = builder.add_node(run.id, "analysis_run", "Analysis run", run.status)
        feature_node = builder.add_node(
            context.feature_snapshot.id if context.feature_snapshot else None,
            "feature_snapshot",
            "Feature snapshot",
        )
        indicator_node = builder.add_node(
            context.indicator_snapshot.id if context.indicator_snapshot else None,
            "indicator_snapshot",
            "Indicator snapshot",
        )
        builder.add_edge(run_node, feature_node, ArtifactRelationship.PRODUCED)
        builder.add_edge(run_node, indicator_node, ArtifactRelationship.PRODUCED)
        for candidate in context.pattern_candidates:
            node = builder.add_node(
                candidate.id,
                "pattern_candidate",
                candidate.pattern_type,
                "selected" if candidate.is_selected else None,
            )
            builder.add_edge(run_node, node, ArtifactRelationship.PRODUCED)
        signal_node = builder.add_node(
            context.signal.id if context.signal else None,
            "signal",
            "Signal",
            context.signal.classification_status if context.signal else None,
        )
        builder.add_edge(run_node, signal_node, ArtifactRelationship.PRODUCED)
        if context.signal is not None:
            self.add_downstream_graph(builder, signal_node, context)
        for replay in context.replay_runs:
            replay_node = builder.add_node(replay.id, "analysis_run", "Replay run", replay.status)
            builder.add_edge(replay_node, run_node, ArtifactRelationship.REPLAYED_FROM)
        return builder.build(include_graph)

    def signal_graph(
        self,
        signal: Signal,
        context: "AnalysisTimelineContext",
        selected_candidate: PatternCandidate | None,
        include_graph: bool,
    ) -> ArtifactGraph:
        builder = ArtifactGraphBuilder()
        run_node = builder.add_node(
            context.run.id,
            "analysis_run",
            "Parent analysis run",
            context.run.status,
        )
        signal_node = builder.add_node(signal.id, "signal", "Signal", signal.classification_status)
        builder.add_edge(run_node, signal_node, ArtifactRelationship.PRODUCED)
        if selected_candidate is not None:
            candidate_node = builder.add_node(
                selected_candidate.id,
                "pattern_candidate",
                selected_candidate.pattern_type,
                "selected",
            )
            builder.add_edge(signal_node, candidate_node, ArtifactRelationship.DERIVED_FROM)
        self.add_downstream_graph(builder, signal_node, context)
        return builder.build(include_graph)

    def add_downstream_graph(
        self,
        builder: ArtifactGraphBuilder,
        signal_node: str | None,
        context: "AnalysisTimelineContext",
    ) -> None:
        explanation_node = builder.add_node(
            context.deterministic_explanation.id if context.deterministic_explanation else None,
            "deterministic_explanation",
            "Deterministic explanation",
            (
                context.deterministic_explanation.safety_status
                if context.deterministic_explanation
                else None
            ),
        )
        builder.add_edge(signal_node, explanation_node, ArtifactRelationship.EXPLAINED_BY)
        for explanation in context.llm_explanations:
            node = builder.add_node(
                explanation.id,
                "llm_explanation",
                "LLM explanation",
                explanation.safety_status,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.EXPLAINED_BY)
        for correlation in context.news_correlations:
            node = builder.add_node(
                correlation.id,
                "signal_news_correlation",
                "News correlation",
                correlation.correlation_label,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.CORRELATED_WITH)
        for outcome in context.outcomes:
            node = builder.add_node(outcome.id, "outcome", "Outcome", outcome.outcome_label)
            builder.add_edge(signal_node, node, ArtifactRelationship.EVALUATED_BY)
        for reasoning_run in context.reasoning_runs:
            node = builder.add_node(
                reasoning_run.id,
                "reasoning_run",
                "Reasoning run",
                reasoning_run.status,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.EXPLAINED_BY)
        for plan in context.action_plans:
            node = builder.add_node(plan.id, "action_plan", "Action plan", plan.status)
            builder.add_edge(signal_node, node, ArtifactRelationship.PLANNED_ACTION)
        for chart_run in context.chart_runs:
            node = builder.add_node(
                chart_run.id,
                "chart_screenshot_run",
                "Chart screenshot run",
                chart_run.status,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.REVIEWED_BY)
        for scan_run in context.scan_runs:
            node = builder.add_node(
                scan_run.id,
                "scheduled_scan_run",
                "Scheduled scan run",
                scan_run.status,
            )
            builder.add_edge(node, signal_node, ArtifactRelationship.PRODUCED)
        for scan_item in context.scan_items:
            node = builder.add_node(
                scan_item.id,
                "scheduled_scan_run_item",
                "Scheduled scan item",
                scan_item.status,
            )
            builder.add_edge(node, signal_node, ArtifactRelationship.PRODUCED)
        for quality_run in context.quality_runs:
            node = builder.add_node(
                quality_run.id,
                "intelligence_quality_run",
                "Quality run",
                quality_run.quality_label,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.EVALUATED_BY)
        for finding in context.quality_findings:
            node = builder.add_node(
                finding.id,
                "intelligence_quality_finding",
                "Quality finding",
                finding.severity,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.EVALUATED_BY)
        for result in context.shadow_results:
            node = builder.add_node(
                result.id,
                "shadow_classification_result",
                "Shadow classification",
                result.agreement_with_final,
            )
            builder.add_edge(signal_node, node, ArtifactRelationship.EVALUATED_BY)

    def reasoning_graph(
        self,
        run: LlmReasoningRun,
        scenarios: list[ScenarioHypothesis],
        plans: list[ReasoningActionPlan],
        include_graph: bool,
    ) -> ArtifactGraph:
        builder = ArtifactGraphBuilder()
        source_node = builder.add_node(
            run.signal_id or run.analysis_run_id or run.outcome_id,
            run.source_type,
            "Reasoning source",
        )
        run_node = builder.add_node(run.id, "reasoning_run", "Reasoning run", run.status)
        builder.add_edge(source_node, run_node, ArtifactRelationship.EXPLAINED_BY)
        for scenario in scenarios:
            scenario_node = builder.add_node(
                scenario.id,
                "scenario_hypothesis",
                scenario.scenario_type,
                scenario.possibility_label,
            )
            builder.add_edge(run_node, scenario_node, ArtifactRelationship.PRODUCED)
        for plan in plans:
            plan_node = builder.add_node(plan.id, "action_plan", "Action plan", plan.status)
            builder.add_edge(run_node, plan_node, ArtifactRelationship.PLANNED_ACTION)
        return builder.build(include_graph)

    def action_plan_graph(
        self,
        plan: ReasoningActionPlan,
        items: list[ReasoningActionItem],
        include_graph: bool,
    ) -> ArtifactGraph:
        builder = ArtifactGraphBuilder()
        source_node = builder.add_node(plan.source_id, plan.source_type, "Action plan source")
        plan_node = builder.add_node(plan.id, "action_plan", "Action plan", plan.status)
        builder.add_edge(source_node, plan_node, ArtifactRelationship.PLANNED_ACTION)
        for item in items:
            item_node = builder.add_node(item.id, "action_item", item.action_type, item.status)
            builder.add_edge(plan_node, item_node, ArtifactRelationship.PRODUCED)
        return builder.build(include_graph)

    def outcome_graph(
        self,
        outcome: SignalOutcome,
        signal: Signal | None,
        run: AnalysisRun | None,
        reasoning_runs: list[LlmReasoningRun],
        action_items: list[ReasoningActionItem],
        include_graph: bool,
    ) -> ArtifactGraph:
        builder = ArtifactGraphBuilder()
        run_node = builder.add_node(run.id if run else None, "analysis_run", "Analysis run")
        signal_node = builder.add_node(signal.id if signal else None, "signal", "Signal")
        builder.add_edge(run_node, signal_node, ArtifactRelationship.PRODUCED)
        outcome_node = builder.add_node(outcome.id, "outcome", "Outcome", outcome.outcome_label)
        builder.add_edge(signal_node, outcome_node, ArtifactRelationship.EVALUATED_BY)
        for reasoning_run in reasoning_runs:
            node = builder.add_node(
                reasoning_run.id,
                "reasoning_run",
                "Reasoning run",
                reasoning_run.status,
            )
            builder.add_edge(outcome_node, node, ArtifactRelationship.EXPLAINED_BY)
        for item in action_items:
            node = builder.add_node(item.id, "action_item", item.action_type, item.status)
            builder.add_edge(node, outcome_node, ArtifactRelationship.EVALUATED_BY)
        return builder.build(include_graph)

    def chart_graph(
        self,
        run: ChartScreenshotRun,
        analysis_run: AnalysisRun | None,
        signal: Signal | None,
        corrections: list[ChartScreenshotRun],
        include_graph: bool,
    ) -> ArtifactGraph:
        builder = ArtifactGraphBuilder()
        chart_node = builder.add_node(
            run.id,
            "chart_screenshot_run",
            "Chart screenshot run",
            run.status,
        )
        analysis_node = builder.add_node(
            analysis_run.id if analysis_run else None,
            "analysis_run",
            "Linked analysis run",
            analysis_run.status if analysis_run else None,
        )
        signal_node = builder.add_node(
            signal.id if signal else None,
            "signal",
            "Linked signal",
            signal.classification_status if signal else None,
        )
        builder.add_edge(chart_node, analysis_node, ArtifactRelationship.PRODUCED)
        builder.add_edge(analysis_node, signal_node, ArtifactRelationship.PRODUCED)
        for correction in corrections:
            node = builder.add_node(
                correction.id,
                "chart_screenshot_run",
                "Chart correction run",
                correction.status,
            )
            builder.add_edge(chart_node, node, ArtifactRelationship.REVIEWED_BY)
        return builder.build(include_graph)

    def analysis_sections(
        self,
        context: "AnalysisTimelineContext",
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "analysis_run": self.analysis_run_metadata(context.run),
            "feature_snapshot": self.snapshot_metadata(context.feature_snapshot, "features_json"),
            "indicator_snapshot": self.snapshot_metadata(
                context.indicator_snapshot,
                "indicators_json",
            ),
            "pattern_candidates": bounded_artifacts(
                [self.pattern_candidate_metadata(item) for item in context.pattern_candidates],
                options.limit_artifacts,
            ),
            "signal": self.signal_metadata(context.signal) if context.signal else None,
            "deterministic_explanation": (
                self.deterministic_explanation_metadata(context.deterministic_explanation)
                if context.deterministic_explanation
                else None
            ),
            "llm_explanations": bounded_artifacts(
                [self.llm_explanation_metadata(item) for item in context.llm_explanations],
                options.limit_artifacts,
            ),
            "outcomes": bounded_artifacts(
                [self.outcome_metadata(item) for item in context.outcomes],
                options.limit_artifacts,
            ),
            "replay_runs": bounded_artifacts(
                [self.analysis_run_metadata(item) for item in context.replay_runs],
                options.limit_artifacts,
            ),
            "scheduled_scan_runs": bounded_artifacts(
                [self.scheduled_scan_run_metadata(item) for item in context.scan_runs],
                options.limit_artifacts,
            ),
            "scheduled_scan_items": bounded_artifacts(
                [self.scheduled_scan_item_metadata(item) for item in context.scan_items],
                options.limit_artifacts,
            ),
            "quality_runs": bounded_artifacts(
                [self.quality_run_metadata(item) for item in context.quality_runs],
                options.limit_artifacts,
            ),
            "quality_findings": bounded_artifacts(
                [self.quality_finding_metadata(item) for item in context.quality_findings],
                options.limit_artifacts,
            ),
            "shadow_classifications": bounded_artifacts(
                [self.shadow_result_metadata(item) for item in context.shadow_results],
                options.limit_artifacts,
            ),
            "raw_candle_series_included": False,
        }

    def signal_sections(
        self,
        signal: Signal,
        context: "AnalysisTimelineContext",
        selected_candidate: PatternCandidate | None,
        diagnostics: dict[str, list[dict[str, Any]]],
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "signal": self.signal_metadata(signal),
            "parent_analysis_run": self.analysis_run_metadata(context.run),
            "strategy_profile_snapshot": safe_metadata(signal.strategy_profile_snapshot_json or {}),
            "selected_pattern_candidate": (
                self.pattern_candidate_metadata(selected_candidate)
                if selected_candidate is not None
                else None
            ),
            "evidence": bounded_artifacts(
                [self.evidence_metadata(item) for item in context.evidence],
                options.limit_artifacts,
            ),
            "confidence_components": bounded_artifacts(
                [self.confidence_metadata(item) for item in context.confidence_components],
                options.limit_artifacts,
            ),
            "risk_notes": bounded_artifacts(
                [self.risk_note_metadata(item) for item in context.risk_notes],
                options.limit_artifacts,
            ),
            "diagnostics": self.signal_diagnostic_sections(diagnostics, options),
        }

    def reasoning_sections(
        self,
        run: LlmReasoningRun,
        scenarios: list[ScenarioHypothesis],
        plans: list[ReasoningActionPlan],
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "reasoning_run": self.reasoning_metadata(run),
            "scenario_hypotheses": bounded_artifacts(
                [self.scenario_metadata(item) for item in scenarios],
                options.limit_artifacts,
            ),
            "action_plans": bounded_artifacts(
                [self.action_plan_metadata(item) for item in plans],
                options.limit_artifacts,
            ),
        }

    def action_plan_sections(
        self,
        plan: ReasoningActionPlan,
        items: list[ReasoningActionItem],
        worker_runs: list[dict[str, Any]],
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "action_plan": self.action_plan_metadata(plan),
            "action_items": bounded_artifacts(
                [self.action_item_metadata(item) for item in items],
                options.limit_artifacts,
            ),
            "rejected_actions": plan.metadata_json.get("rejectedActions", []),
            "skipped_actions": plan.metadata_json.get("skippedActions", []),
            "worker_runs": bounded_artifacts(worker_runs, options.limit_artifacts),
            "actions_executed_by_timeline": False,
        }

    def outcome_sections(
        self,
        outcome: SignalOutcome,
        signal: Signal | None,
        run: AnalysisRun | None,
        reasoning_runs: list[LlmReasoningRun],
        action_items: list[ReasoningActionItem],
        diagnostics: dict[str, list[dict[str, Any]]],
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "outcome": self.outcome_metadata(outcome),
            "parent_signal": self.signal_metadata(signal) if signal is not None else None,
            "parent_analysis_run": self.analysis_run_metadata(run) if run is not None else None,
            "reasoning_runs": bounded_artifacts(
                [self.reasoning_metadata(item) for item in reasoning_runs],
                options.limit_artifacts,
            ),
            "linked_action_items": bounded_artifacts(
                [self.action_item_metadata(item) for item in action_items],
                options.limit_artifacts,
            ),
            "diagnostics": {
                key: bounded_artifacts(value, options.limit_artifacts)
                for key, value in diagnostics.items()
            },
        }

    def chart_sections(
        self,
        run: ChartScreenshotRun,
        analysis_run: AnalysisRun | None,
        signal: Signal | None,
        corrections: list[ChartScreenshotRun],
        quality_runs: list[IntelligenceQualityRun],
        quality_findings: list[IntelligenceQualityFinding],
        shadow_results: list[ShadowClassificationResult],
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "chart_screenshot_run": self.chart_screenshot_metadata(run),
            "linked_analysis_run": (
                self.analysis_run_metadata(analysis_run) if analysis_run is not None else None
            ),
            "linked_signal": self.signal_metadata(signal) if signal is not None else None,
            "human_review": self.human_review(run),
            "corrections": bounded_artifacts(
                [self.chart_screenshot_metadata(item) for item in corrections],
                options.limit_artifacts,
            ),
            "quality_runs": bounded_artifacts(
                [self.quality_run_metadata(item) for item in quality_runs],
                options.limit_artifacts,
            ),
            "quality_findings": bounded_artifacts(
                [self.quality_finding_metadata(item) for item in quality_findings],
                options.limit_artifacts,
            ),
            "shadow_classifications": bounded_artifacts(
                [self.shadow_result_metadata(item) for item in shadow_results],
                options.limit_artifacts,
            ),
            "raw_image_bytes_included": False,
            "raw_candle_series_included": False,
        }

    def signal_diagnostic_sections(
        self,
        diagnostics: dict[str, list[Any]],
        options: AuditTimelineOptions,
    ) -> dict[str, Any]:
        return {
            "profile_diagnostics": bounded_artifacts(
                diagnostics.get("profile_diagnostics", []),
                options.limit_artifacts,
            ),
            "pattern_diagnostics": bounded_artifacts(
                diagnostics.get("pattern_diagnostics", []),
                options.limit_artifacts,
            ),
            "calibration_recommendations": bounded_artifacts(
                diagnostics.get("calibration_recommendations", []),
                options.limit_artifacts,
            ),
            "quality_runs": bounded_artifacts(
                [
                    self.quality_run_metadata(item)
                    for item in diagnostics.get("quality_runs", [])
                    if isinstance(item, IntelligenceQualityRun)
                ],
                options.limit_artifacts,
            ),
            "quality_findings": bounded_artifacts(
                [
                    self.quality_finding_metadata(item)
                    for item in diagnostics.get("quality_findings", [])
                    if isinstance(item, IntelligenceQualityFinding)
                ],
                options.limit_artifacts,
            ),
            "shadow_classifications": bounded_artifacts(
                [
                    self.shadow_result_metadata(item)
                    for item in diagnostics.get("shadow_results", [])
                    if isinstance(item, ShadowClassificationResult)
                ],
                options.limit_artifacts,
            ),
        }

    def analysis_run_metadata(self, run: AnalysisRun | None) -> dict[str, Any]:
        if run is None:
            return {}
        return {
            "id": run.id,
            "workspace_id": run.workspace_id,
            "symbol_id": run.symbol_id,
            "source_id": run.source_id,
            "timeframe": run.timeframe,
            "start_time": run.start_time,
            "end_time": run.end_time,
            "warmup_start_time": run.warmup_start_time,
            "baseline_start_time": run.baseline_start_time,
            "analysis_mode": run.analysis_mode,
            "include_partial_live_candle": run.include_partial_live_candle,
            "include_news_correlation": run.include_news_correlation,
            "include_ai_explanation": run.include_ai_explanation,
            "status": run.status,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "engine_version": run.engine_version,
            "rule_set_version": run.rule_set_version,
            "replayed_from_analysis_run_id": run.replayed_from_analysis_run_id,
            "replay_mode": run.replay_mode,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
        }

    def signal_metadata(self, signal: Signal | None) -> dict[str, Any]:
        if signal is None:
            return {}
        return {
            "id": signal.id,
            "analysis_run_id": signal.analysis_run_id,
            "workspace_id": signal.workspace_id,
            "symbol_id": signal.symbol_id,
            "timeframe": signal.timeframe,
            "strategy_profile_id": signal.strategy_profile_id,
            "strategy_profile_key": signal.strategy_profile_key,
            "strategy_profile_version": signal.strategy_profile_version,
            "classification_status": signal.classification_status,
            "bias": signal.bias,
            "pattern_type": signal.pattern_type,
            "confidence_score": signal.confidence_score,
            "confidence_label": signal.confidence_label,
            "candidate_strength": signal.candidate_strength,
            "selected_pattern_candidate_id": signal.selected_pattern_candidate_id,
            "movement_direction": signal.movement_direction,
            "movement_quality": signal.movement_quality,
            "volatility_state": signal.volatility_state,
            "trend_state": signal.trend_state,
            "range_state": signal.range_state,
            "summary": signal.summary,
            "no_signal_reason": signal.no_signal_reason,
            "created_at": signal.created_at,
        }

    def snapshot_metadata(
        self,
        snapshot: FeatureSnapshot | IndicatorSnapshot | None,
        field_name: str,
    ) -> dict[str, Any]:
        if snapshot is None:
            return {"present": False}
        payload = getattr(snapshot, field_name)
        return {
            "present": True,
            "id": snapshot.id,
            "analysis_run_id": snapshot.analysis_run_id,
            "workspace_id": snapshot.workspace_id,
            "symbol_id": snapshot.symbol_id,
            "timeframe": snapshot.timeframe,
            "key_count": len(payload),
            "keys": sorted(payload.keys())[:50],
            "created_at": snapshot.created_at,
        }

    def pattern_candidate_metadata(self, candidate: PatternCandidate | None) -> dict[str, Any]:
        if candidate is None:
            return {}
        return {
            "id": candidate.id,
            "analysis_run_id": candidate.analysis_run_id,
            "pattern_type": candidate.pattern_type,
            "bias": candidate.bias,
            "strength_score": candidate.strength_score,
            "is_selected": candidate.is_selected,
            "evidence": candidate.evidence_json,
            "risk_notes": candidate.risk_notes_json,
            "metrics": candidate.metrics_json,
            "created_at": candidate.created_at,
        }

    def evidence_metadata(self, item: SignalEvidence) -> dict[str, Any]:
        return {
            "id": item.id,
            "signal_id": item.signal_id,
            "evidence_type": item.evidence_type,
            "direction": item.direction,
            "message": item.message,
            "numeric_value": item.numeric_value,
            "weight": item.weight,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def confidence_metadata(self, item: SignalConfidenceComponent) -> dict[str, Any]:
        return {
            "id": item.id,
            "signal_id": item.signal_id,
            "component_name": item.component_name,
            "component_score": item.component_score,
            "component_weight": item.component_weight,
            "weighted_score": item.weighted_score,
            "reason": item.reason,
            "created_at": item.created_at,
        }

    def risk_note_metadata(self, item: SignalRiskNote) -> dict[str, Any]:
        return {
            "id": item.id,
            "signal_id": item.signal_id,
            "code": item.code,
            "message": item.message,
            "severity": item.severity,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def deterministic_explanation_metadata(
        self,
        item: DeterministicExplanation,
    ) -> dict[str, Any]:
        return {
            "id": item.id,
            "signal_id": item.signal_id,
            "analysis_run_id": item.analysis_run_id,
            "template_version": item.template_version,
            "explanation_type": item.explanation_type,
            "short_summary": item.short_summary,
            "safety_status": item.safety_status,
            "blocked_terms": item.blocked_terms_json,
            "created_at": item.created_at,
        }

    def llm_explanation_metadata(self, item: LlmExplanation) -> dict[str, Any]:
        return {
            "id": item.id,
            "signal_id": item.signal_id,
            "analysis_run_id": item.analysis_run_id,
            "provider": item.provider,
            "model": item.model,
            "prompt_version": item.prompt_version,
            "safety_status": item.safety_status,
            "grounding_status": item.grounding_status,
            "grounding_issues": item.grounding_issues_json,
            "tokens_input": item.tokens_input,
            "tokens_output": item.tokens_output,
            "estimated_cost": item.estimated_cost,
            "created_at": item.created_at,
        }

    def outcome_metadata(self, item: SignalOutcome) -> dict[str, Any]:
        return {
            "id": item.id,
            "analysis_run_id": item.analysis_run_id,
            "signal_id": item.signal_id,
            "horizon_minutes": item.horizon_minutes,
            "evaluation_status": item.evaluation_status,
            "reference_time": item.reference_time,
            "reference_price": item.reference_price,
            "future_window_start": item.future_window_start,
            "future_window_end": item.future_window_end,
            "future_candle_count": item.future_candle_count,
            "max_favorable_move": item.max_favorable_move,
            "max_adverse_move": item.max_adverse_move,
            "net_move": item.net_move,
            "max_favorable_pips": item.max_favorable_pips,
            "max_adverse_pips": item.max_adverse_pips,
            "net_pips": item.net_pips,
            "direction_followed": item.direction_followed,
            "reversal_detected": item.reversal_detected,
            "outcome_label": item.outcome_label,
            "movement_quality": item.movement_quality,
            "evaluation_version": item.evaluation_version,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def reasoning_metadata(self, item: LlmReasoningRun) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "analysis_run_id": item.analysis_run_id,
            "signal_id": item.signal_id,
            "outcome_id": item.outcome_id,
            "source_type": item.source_type,
            "provider": item.provider,
            "model": item.model,
            "prompt_version": item.prompt_version,
            "reasoning_type": item.reasoning_type,
            "status": item.status,
            "safety_status": item.safety_status,
            "grounding_status": item.grounding_status,
            "blocked_terms": item.blocked_terms_json,
            "grounding_issues": item.grounding_issues_json,
            "tokens_input": item.tokens_input,
            "tokens_output": item.tokens_output,
            "estimated_cost": item.estimated_cost,
            "latency_ms": item.latency_ms,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def scenario_metadata(self, item: ScenarioHypothesis) -> dict[str, Any]:
        return {
            "id": item.id,
            "reasoning_run_id": item.reasoning_run_id,
            "signal_id": item.signal_id,
            "analysis_run_id": item.analysis_run_id,
            "scenario_type": item.scenario_type,
            "scenario_label": item.scenario_label,
            "possibility_label": item.possibility_label,
            "supporting_evidence": item.supporting_evidence_json,
            "conflicting_evidence": item.conflicting_evidence_json,
            "outcome_history": item.outcome_history_json,
            "next_observations": item.next_observations_json,
            "suggested_backend_actions": item.suggested_backend_actions_json,
            "risk_notes": item.risk_notes_json,
            "sort_order": item.sort_order,
            "created_at": item.created_at,
        }

    def action_plan_metadata(self, item: ReasoningActionPlan) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "source_type": item.source_type,
            "source_id": item.source_id,
            "signal_id": item.signal_id,
            "analysis_run_id": item.analysis_run_id,
            "reasoning_run_id": item.reasoning_run_id,
            "status": item.status,
            "plan_version": item.plan_version,
            "created_from": item.created_from,
            "summary": item.summary,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def action_item_metadata(self, item: ReasoningActionItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
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
            "last_attempted_at": item.last_attempted_at,
            "completed_at": item.completed_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def chart_screenshot_metadata(self, item: ChartScreenshotRun) -> dict[str, Any]:
        parser_metadata = item.parser_metadata_json or {}
        extracted_payload = (
            item.extracted_payload_json if isinstance(item.extracted_payload_json, dict) else {}
        )
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "source_id": item.source_id,
            "symbol_id": item.symbol_id,
            "analysis_run_id": item.analysis_run_id,
            "timeframe": item.timeframe,
            "file_name": item.file_name,
            "parser_name": item.parser_name,
            "parser_version": item.parser_version,
            "parser_source_path": item.parser_source_path,
            "status": item.status,
            "extraction_confidence": item.extraction_confidence,
            "raw_candle_count": item.raw_candle_count,
            "stored_candle_count": item.stored_candle_count,
            "duplicate_count": item.duplicate_count,
            "conflict_count": item.conflict_count,
            "analysis_hypothesis": item.analysis_hypothesis,
            "analysis_hypothesis_confidence": item.analysis_hypothesis_confidence,
            "extracted_window_start": item.extracted_window_start,
            "extracted_window_end": item.extracted_window_end,
            "chart_type": parser_metadata.get("chartType"),
            "supported_for_analysis": parser_metadata.get("supportedForAnalysis"),
            "analysis_blocked_reason": parser_metadata.get("analysisBlockedReason"),
            "preview_mode": parser_metadata.get("previewMode"),
            "trigger_analysis": parser_metadata.get("triggerAnalysis"),
            "ocr": parser_metadata.get("ocr"),
            "axis_calibration": parser_metadata.get("axisCalibration"),
            "trend_metrics": extracted_payload.get("trendMetrics"),
            "warnings": item.extraction_warnings_json,
            "human_review": self.human_review(item),
            "created_at": item.created_at,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "updated_at": item.updated_at,
        }

    def scheduled_scan_run_metadata(self, item: ScheduledScanRun) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "scan_config_id": item.scan_config_id,
            "status": item.status,
            "scan_mode": item.scan_mode,
            "scheduled_for": item.scheduled_for,
            "started_at": item.started_at,
            "completed_at": item.completed_at,
            "scanned_item_count": item.scanned_item_count,
            "analysis_run_count": item.analysis_run_count,
            "skipped_count": item.skipped_count,
            "failed_count": item.failed_count,
            "analysis_run_ids": item.analysis_run_ids_json,
            "signal_ids": item.signal_ids_json,
            "reasoning_run_ids": item.reasoning_run_ids_json,
            "action_plan_ids": item.action_plan_ids_json,
            "result": item.result_json,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def scheduled_scan_item_metadata(self, item: ScheduledScanRunItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "scan_run_id": item.scan_run_id,
            "scan_config_id": item.scan_config_id,
            "watchlist_item_id": item.watchlist_item_id,
            "symbol_id": item.symbol_id,
            "source_id": item.source_id,
            "timeframe": item.timeframe,
            "status": item.status,
            "analysis_run_id": item.analysis_run_id,
            "signal_id": item.signal_id,
            "reasoning_run_id": item.reasoning_run_id,
            "action_plan_id": item.action_plan_id,
            "skipped_reason": item.skipped_reason,
            "error_message": item.error_message,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def quality_run_metadata(self, item: IntelligenceQualityRun) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "analysis_run_id": item.analysis_run_id,
            "signal_id": item.signal_id,
            "source_type": item.source_type,
            "status": item.status,
            "quality_score": item.quality_score,
            "quality_label": item.quality_label,
            "gate_version": item.gate_version,
            "shadow_version": item.shadow_version,
            "checked_at": item.checked_at,
            "summary": item.summary,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    def quality_finding_metadata(self, item: IntelligenceQualityFinding) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "quality_run_id": item.quality_run_id,
            "finding_type": item.finding_type,
            "severity": item.severity,
            "code": item.code,
            "title": item.title,
            "message": item.message,
            "artifact_type": item.artifact_type,
            "artifact_id": item.artifact_id,
            "expected_value": item.expected_value,
            "observed_value": item.observed_value,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def shadow_result_metadata(self, item: ShadowClassificationResult) -> dict[str, Any]:
        return {
            "id": item.id,
            "workspace_id": item.workspace_id,
            "quality_run_id": item.quality_run_id,
            "analysis_run_id": item.analysis_run_id,
            "signal_id": item.signal_id,
            "strategy_profile_key": item.strategy_profile_key,
            "strategy_profile_version": item.strategy_profile_version,
            "classification_status": item.classification_status,
            "bias": item.bias,
            "pattern_type": item.pattern_type,
            "confidence_score": item.confidence_score,
            "confidence_label": item.confidence_label,
            "selected_candidate_id": item.selected_candidate_id,
            "agreement_with_final": item.agreement_with_final,
            "disagreement_reason": item.disagreement_reason,
            "metadata": item.metadata_json,
            "created_at": item.created_at,
        }

    def human_review(self, item: ChartScreenshotRun) -> dict[str, Any] | None:
        review = (item.parser_metadata_json or {}).get("humanReview")
        return review if isinstance(review, dict) else None

    def status_severity(self, status: str | None) -> AuditTimelineSeverity:
        if status in {"failed", "blocked", "analysis_failed"}:
            return AuditTimelineSeverity.ERROR
        if status in {
            "fallback_used",
            "review_required",
            "insufficient_data",
            "insufficient_future_data",
            "skipped",
            "completed_with_warnings",
        }:
            return AuditTimelineSeverity.WARNING
        return AuditTimelineSeverity.INFO


class AnalysisTimelineContext:
    def __init__(
        self,
        run: AnalysisRun,
        signal: Signal | None,
        feature_snapshot: FeatureSnapshot | None,
        indicator_snapshot: IndicatorSnapshot | None,
        pattern_candidates: list[PatternCandidate],
        evidence: list[SignalEvidence],
        confidence_components: list[SignalConfidenceComponent],
        risk_notes: list[SignalRiskNote],
        deterministic_explanation: DeterministicExplanation | None,
        llm_explanations: list[LlmExplanation],
        news_correlations: list[SignalNewsCorrelation],
        outcomes: list[SignalOutcome],
        reasoning_runs: list[LlmReasoningRun],
        action_plans: list[ReasoningActionPlan],
        replay_runs: list[AnalysisRun],
        chart_runs: list[ChartScreenshotRun],
        scan_items: list[ScheduledScanRunItem],
        scan_runs: list[ScheduledScanRun],
        quality_runs: list[IntelligenceQualityRun],
        quality_findings: list[IntelligenceQualityFinding],
        shadow_results: list[ShadowClassificationResult],
        audit_logs: list[AnalysisAuditLog],
    ) -> None:
        self.run = run
        self.signal = signal
        self.feature_snapshot = feature_snapshot
        self.indicator_snapshot = indicator_snapshot
        self.pattern_candidates = pattern_candidates
        self.evidence = evidence
        self.confidence_components = confidence_components
        self.risk_notes = risk_notes
        self.deterministic_explanation = deterministic_explanation
        self.llm_explanations = llm_explanations
        self.news_correlations = news_correlations
        self.outcomes = outcomes
        self.reasoning_runs = reasoning_runs
        self.action_plans = action_plans
        self.replay_runs = replay_runs
        self.chart_runs = chart_runs
        self.scan_items = scan_items
        self.scan_runs = scan_runs
        self.quality_runs = quality_runs
        self.quality_findings = quality_findings
        self.shadow_results = shadow_results
        self.audit_logs = audit_logs
