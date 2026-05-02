from typing import Any
from uuid import UUID

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.chart_screenshots.models import ChartScreenshotRun
from app.modules.data_sources.models import DataSource
from app.modules.explanations.models import DeterministicExplanation
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.llm_explanations.models import LlmExplanation
from app.modules.news.models import NewsEvent, SignalNewsCorrelation
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.reasoning.models import LlmReasoningRun, ScenarioHypothesis
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.strategy_profiles.models import StrategyProfile
from app.modules.symbols.models import Symbol
from app.modules.context_packs.limits import ContextPackLimits
from app.modules.context_packs.redaction import (
    ContextPackRedactionState,
    bounded_items,
    safe_value,
    summarize_snapshot,
)
from app.modules.context_packs.repository import ContextPackRepository
from app.modules.context_packs.schemas import ContextPackOptions


class ContextPackBuilders:
    def __init__(
        self,
        repository: ContextPackRepository,
        limits: ContextPackLimits,
        options: ContextPackOptions,
        state: ContextPackRedactionState,
        missing_sections: list[str],
        warnings: list[str],
    ) -> None:
        self.repository = repository
        self.limits = limits
        self.options = options
        self.state = state
        self.missing_sections = missing_sections
        self.warnings = warnings

    async def signal_sections(self, signal: Signal) -> dict[str, Any]:
        analysis_run = await self.repository.get_analysis_run(signal.analysis_run_id)
        symbol = await self.repository.get_symbol(signal.symbol_id)
        strategy_profile = await self.repository.get_strategy_profile(
            signal.strategy_profile_key,
            signal.strategy_profile_version,
        )
        selected_candidate = await self.repository.get_selected_pattern_candidate(signal)
        evidence = await self.repository.list_evidence(signal.id, self.limits.max_evidence_rows)
        confidence_components = await self.repository.list_confidence_components(signal.id)
        risk_notes = await self.repository.list_risk_notes(signal.id, self.limits.max_risk_notes)
        deterministic_explanation = await self.repository.get_deterministic_explanation_by_signal_id(
            signal.id
        )
        llm_explanation = await self.repository.get_llm_explanation_by_signal_id(signal.id)
        correlations = await self.repository.list_news_correlations_by_signal_id(
            signal.id,
            self.limits.max_news_correlations,
        )
        news_events = await self.news_events(correlations)
        outcomes = (
            await self.repository.list_signal_outcomes(signal.id, self.limits.max_outcomes)
            if self.options.include_outcomes
            else []
        )
        reasoning_runs = (
            await self.repository.list_reasoning_runs_by_signal_id(
                signal.id,
                self.limits.max_scenarios,
            )
            if self.options.include_reasoning
            else []
        )
        action_plans = (
            await self.repository.list_action_plans_by_signal_id(signal.id)
            if self.options.include_actions
            else []
        )
        action_items = (
            await self.repository.list_action_items(
                [plan.id for plan in action_plans],
                self.limits.max_action_items,
            )
            if self.options.include_actions
            else []
        )
        audit_logs = (
            await self.repository.list_audit_logs(
                signal.analysis_run_id,
                self.limits.max_audit_events,
            )
            if self.options.include_audit
            else []
        )
        screenshot_runs = (
            await self.repository.list_chart_screenshot_runs_by_analysis_run_id(
                signal.analysis_run_id
            )
            if self.options.include_screenshots
            else []
        )
        return self.safe_sections(
            {
                "signalSummary": self.signal_summary(signal, symbol),
                "analysisRunMetadata": (
                    self.analysis_run_metadata(analysis_run, symbol) if analysis_run else None
                ),
                "marketContext": self.market_context(signal, symbol),
                "strategyProfileSnapshot": self.strategy_profile_section(
                    signal,
                    strategy_profile,
                ),
                "selectedPatternCandidate": self.pattern_candidate_row(selected_candidate),
                "evidence": bounded_items(
                    "sections.evidence",
                    [self.evidence_row(item) for item in evidence],
                    self.limits.max_evidence_rows,
                    self.state,
                    self.limits.max_text_length,
                ),
                "confidenceComponents": bounded_items(
                    "sections.confidenceComponents",
                    [self.confidence_component_row(item) for item in confidence_components],
                    len(confidence_components),
                    self.state,
                    self.limits.max_text_length,
                ),
                "riskNotes": bounded_items(
                    "sections.riskNotes",
                    [self.risk_note_row(item) for item in risk_notes],
                    self.limits.max_risk_notes,
                    self.state,
                    self.limits.max_text_length,
                ),
                "deterministicExplanation": self.deterministic_explanation_section(
                    deterministic_explanation
                ),
                "llmExplanation": self.llm_explanation_section(llm_explanation),
                "newsCorrelations": self.news_correlation_section(correlations, news_events),
                "outcomes": self.outcomes_section(outcomes, self.options.include_outcomes),
                "advancedFeatures": await self.optional_signal_section(
                    "advancedFeatures",
                    "select id, analysis_run_id, signal_id, feature_family, summary_json, "
                    "metadata_json, created_at from advanced_feature_snapshots "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    20,
                ),
                "marketRegime": await self.optional_signal_section(
                    "marketRegime",
                    "select id, analysis_run_id, signal_id, regime_label, confidence_score, "
                    "evidence_json, metadata_json, created_at from market_regime_snapshots "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    5,
                ),
                "marketSession": await self.optional_signal_section(
                    "marketSession",
                    "select id, analysis_run_id, signal_id, session_label, timezone, "
                    "metadata_json, created_at from market_session_snapshots "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    5,
                ),
                "multiTimeframeContext": await self.optional_signal_section(
                    "multiTimeframeContext",
                    "select id, analysis_run_id, signal_id, timeframe, alignment_label, "
                    "context_json, created_at from multi_timeframe_contexts "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    20,
                ),
                "historicalCases": await self.optional_signal_section(
                    "historicalCases",
                    "select id, signal_id, analysis_run_id, match_score, case_summary, "
                    "outcome_label, metadata_json, created_at from historical_case_matches "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by match_score desc nulls last, created_at desc limit :limit",
                    signal,
                    20,
                ),
                "diagnostics": await self.optional_signal_context_section(
                    "diagnostics",
                    "select id, diagnostic_run_id, strategy_profile_key, "
                    "strategy_profile_version, symbol_id, timeframe, horizon_minutes, "
                    "sample_size, evaluated_count, diagnostic_label, diagnostic_summary, "
                    "metadata_json, created_at from strategy_profile_diagnostics "
                    "where workspace_id = :workspace_id "
                    "and (:strategy_profile_key is null or strategy_profile_key = :strategy_profile_key) "
                    "and (:symbol_id is null or symbol_id = :symbol_id) "
                    "and (:timeframe is null or timeframe = :timeframe) "
                    "order by created_at desc limit :limit",
                    signal,
                    20,
                    self.options.include_diagnostics,
                ),
                "reasoningRuns": self.reasoning_runs_section(
                    reasoning_runs,
                    self.options.include_reasoning,
                ),
                "actionPlans": self.action_plans_section(
                    action_plans,
                    action_items,
                    self.options.include_actions,
                ),
                "qualityRuns": await self.optional_signal_section(
                    "qualityRuns",
                    "select id, signal_id, analysis_run_id, status, score, findings_json, "
                    "metadata_json, created_at from quality_gate_runs "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    20,
                    self.options.include_quality,
                ),
                "decisionReadiness": await self.optional_signal_section(
                    "decisionReadiness",
                    "select id, signal_id, analysis_run_id, readiness_label, blockers_json, "
                    "checks_json, metadata_json, created_at from decision_readiness_snapshots "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    10,
                    self.options.include_quality,
                ),
                "intelligenceReports": await self.optional_signal_section(
                    "intelligenceReports",
                    "select id, signal_id, analysis_run_id, report_type, status, "
                    "summary_json, metadata_json, created_at from intelligence_report_artifacts "
                    "where signal_id = :signal_id or analysis_run_id = :analysis_run_id "
                    "order by created_at desc limit :limit",
                    signal,
                    20,
                    self.options.include_reports,
                ),
                "auditTimeline": self.audit_section(audit_logs, self.options.include_audit),
                "reproducibilityManifest": (
                    self.reproducibility_manifest(analysis_run) if analysis_run else None
                ),
                "screenshotArtifacts": self.screenshot_runs_section(
                    screenshot_runs,
                    self.options.include_screenshots,
                ),
            }
        )

    async def analysis_run_sections(self, run: AnalysisRun) -> dict[str, Any]:
        symbol = await self.repository.get_symbol(run.symbol_id)
        source = await self.repository.get_data_source(run.source_id)
        signal = await self.repository.get_signal_by_analysis_run_id(run.id)
        feature_snapshot = await self.repository.get_feature_snapshot(run.id)
        indicator_snapshot = await self.repository.get_indicator_snapshot(run.id)
        candidates = await self.repository.list_pattern_candidates(run.id)
        deterministic_explanation = await self.repository.get_deterministic_explanation_by_analysis_run_id(
            run.id
        )
        correlations = await self.repository.list_news_correlations_by_analysis_run_id(
            run.id,
            self.limits.max_news_correlations,
        )
        news_events = await self.news_events(correlations)
        outcomes = (
            await self.repository.list_analysis_outcomes(run.id, self.limits.max_outcomes)
            if self.options.include_outcomes
            else []
        )
        replays = await self.repository.list_replay_links(run.id)
        audit_logs = (
            await self.repository.list_audit_logs(run.id, self.limits.max_audit_events)
            if self.options.include_audit
            else []
        )
        action_plans = (
            await self.repository.list_action_plans_by_analysis_run_id(run.id)
            if self.options.include_actions
            else []
        )
        action_items = (
            await self.repository.list_action_items(
                [plan.id for plan in action_plans],
                self.limits.max_action_items,
            )
            if self.options.include_actions
            else []
        )
        return self.safe_sections(
            {
                "analysisRunMetadata": self.analysis_run_metadata(run, symbol),
                "candlePolicy": self.candle_policy(run),
                "sourceMetadata": self.source_metadata(source),
                "featureSnapshotSummary": self.feature_snapshot_section(feature_snapshot),
                "indicatorSnapshotSummary": self.indicator_snapshot_section(indicator_snapshot),
                "advancedFeatureSnapshot": await self.optional_analysis_section(
                    "advancedFeatureSnapshot",
                    "select id, analysis_run_id, feature_family, summary_json, metadata_json, "
                    "created_at from advanced_feature_snapshots "
                    "where analysis_run_id = :analysis_run_id order by created_at desc limit :limit",
                    run.id,
                    20,
                ),
                "patternCandidates": bounded_items(
                    "sections.patternCandidates",
                    [self.pattern_candidate_row(candidate) for candidate in candidates],
                    25,
                    self.state,
                    self.limits.max_text_length,
                ),
                "signalSummary": self.signal_summary(signal, symbol) if signal else None,
                "deterministicExplanation": self.deterministic_explanation_section(
                    deterministic_explanation
                ),
                "newsCorrelations": self.news_correlation_section(correlations, news_events),
                "outcomes": self.outcomes_section(outcomes, self.options.include_outcomes),
                "replayLinks": bounded_items(
                    "sections.replayLinks",
                    [self.replay_row(replay) for replay in replays],
                    20,
                    self.state,
                    self.limits.max_text_length,
                ),
                "actionPlans": self.action_plans_section(
                    action_plans,
                    action_items,
                    self.options.include_actions,
                ),
                "auditEvents": self.audit_section(audit_logs, self.options.include_audit),
                "eventStudies": await self.optional_analysis_section(
                    "eventStudies",
                    "select id, analysis_run_id, event_type, event_window_json, result_json, "
                    "metadata_json, created_at from event_studies "
                    "where analysis_run_id = :analysis_run_id order by created_at desc limit :limit",
                    run.id,
                    20,
                ),
                "intelligenceReports": await self.optional_analysis_section(
                    "intelligenceReports",
                    "select id, analysis_run_id, report_type, status, summary_json, "
                    "metadata_json, created_at from intelligence_report_artifacts "
                    "where analysis_run_id = :analysis_run_id order by created_at desc limit :limit",
                    run.id,
                    20,
                    self.options.include_reports,
                ),
            }
        )

    async def reasoning_run_sections(self, run: LlmReasoningRun) -> dict[str, Any]:
        signal = await self.repository.get_signal(run.signal_id) if run.signal_id else None
        scenarios = await self.repository.list_scenario_hypotheses(
            run.id,
            self.limits.max_scenarios,
        )
        action_plans = (
            await self.repository.list_action_plans_by_reasoning_run_id(run.id)
            if self.options.include_actions
            else []
        )
        action_items = (
            await self.repository.list_action_items(
                [plan.id for plan in action_plans],
                self.limits.max_action_items,
            )
            if self.options.include_actions
            else []
        )
        return self.safe_sections(
            {
                "reasoningRunMetadata": self.reasoning_run_metadata(run),
                "inputSnapshotSummary": summarize_snapshot(
                    "sections.inputSnapshotSummary",
                    run.input_snapshot_json,
                    self.state,
                    self.limits.max_text_length,
                ),
                "scenarioHypotheses": bounded_items(
                    "sections.scenarioHypotheses",
                    [self.scenario_row(scenario) for scenario in scenarios],
                    self.limits.max_scenarios,
                    self.state,
                    self.limits.max_text_length,
                ),
                "safetyGroundingStatus": self.reasoning_safety_section(run),
                "actionPlan": self.action_plans_section(
                    action_plans,
                    action_items,
                    self.options.include_actions,
                ),
                "signalSummary": self.signal_summary(signal, None) if signal else None,
                "blockedGroundingIssues": {
                    "blockedTerms": run.blocked_terms_json,
                    "groundingIssues": run.grounding_issues_json,
                    "errorMessage": run.error_message,
                },
            }
        )

    async def outcome_sections(self, outcome: SignalOutcome) -> dict[str, Any]:
        signal = await self.repository.get_signal(outcome.signal_id)
        analysis_run = await self.repository.get_analysis_run(outcome.analysis_run_id)
        symbol = await self.repository.get_symbol(outcome.symbol_id)
        selected_candidate = (
            await self.repository.get_selected_pattern_candidate(signal) if signal else None
        )
        return self.safe_sections(
            {
                "outcomeMetadata": self.outcome_row(outcome),
                "parentSignal": self.signal_summary(signal, symbol) if signal else None,
                "horizon": {
                    "horizonMinutes": outcome.horizon_minutes,
                    "referenceTime": outcome.reference_time,
                    "futureWindowStart": outcome.future_window_start,
                    "futureWindowEnd": outcome.future_window_end,
                    "futureCandleCount": outcome.future_candle_count,
                },
                "movement": {
                    "maxFavorableMove": outcome.max_favorable_move,
                    "maxAdverseMove": outcome.max_adverse_move,
                    "netMove": outcome.net_move,
                    "maxFavorablePips": outcome.max_favorable_pips,
                    "maxAdversePips": outcome.max_adverse_pips,
                    "netPips": outcome.net_pips,
                    "maxFavorableTicks": outcome.max_favorable_ticks,
                    "maxAdverseTicks": outcome.max_adverse_ticks,
                    "netTicks": outcome.net_ticks,
                },
                "label": {
                    "evaluationStatus": outcome.evaluation_status,
                    "outcomeLabel": outcome.outcome_label,
                    "movementQuality": outcome.movement_quality,
                    "directionFollowed": outcome.direction_followed,
                    "reversalDetected": outcome.reversal_detected,
                },
                "parentAnalysisRun": (
                    self.analysis_run_metadata(analysis_run, symbol) if analysis_run else None
                ),
                "relatedProfilePatternSessionRegime": {
                    "strategyProfileKey": outcome.strategy_profile_key,
                    "strategyProfileVersion": outcome.strategy_profile_version,
                    "patternType": outcome.pattern_type,
                    "selectedPatternCandidate": self.pattern_candidate_row(selected_candidate),
                    "session": await self.optional_analysis_section(
                        "outcome.session",
                        "select id, analysis_run_id, session_label, timezone, metadata_json, "
                        "created_at from market_session_snapshots "
                        "where analysis_run_id = :analysis_run_id order by created_at desc limit 1",
                        outcome.analysis_run_id,
                        1,
                    ),
                    "regime": await self.optional_analysis_section(
                        "outcome.regime",
                        "select id, analysis_run_id, regime_label, confidence_score, evidence_json, "
                        "metadata_json, created_at from market_regime_snapshots "
                        "where analysis_run_id = :analysis_run_id order by created_at desc limit 1",
                        outcome.analysis_run_id,
                        1,
                    ),
                },
            }
        )

    async def chart_screenshot_run_sections(self, run: ChartScreenshotRun) -> dict[str, Any]:
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
        symbol = await self.repository.get_symbol(run.symbol_id)
        return self.safe_sections(
            {
                "screenshotRunMetadata": self.chart_screenshot_row(run),
                "parserExtractionMetadata": self.parser_extraction_metadata(run),
                "ocrStatus": {
                    "status": run.ocr_status,
                    "confidence": run.ocr_confidence,
                    "axisCalibration": run.axis_calibration_json,
                },
                "reviewCorrectionState": self.review_correction_state(run),
                "linkedAnalysis": (
                    self.analysis_run_metadata(analysis_run, symbol) if analysis_run else None
                ),
                "linkedSignal": self.signal_summary(signal, symbol) if signal else None,
                "extractedPayloadSummary": summarize_snapshot(
                    "sections.extractedPayloadSummary",
                    run.extracted_payload_json,
                    self.state,
                    self.limits.max_text_length,
                ),
                "warnings": run.extraction_warnings_json,
            }
        )

    async def optional_signal_section(
        self,
        section_name: str,
        statement_text: str,
        signal: Signal,
        limit: int,
        included: bool = True,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        rows = await self.repository.optional_rows(
            statement_text,
            {
                "signal_id": signal.id,
                "analysis_run_id": signal.analysis_run_id,
                "limit": limit + 1,
            },
        )
        if not rows:
            self.missing_sections.append(section_name)
        return bounded_items(
            f"sections.{section_name}",
            rows,
            limit,
            self.state,
            self.limits.max_text_length,
        )

    async def optional_analysis_section(
        self,
        section_name: str,
        statement_text: str,
        analysis_run_id: UUID,
        limit: int,
        included: bool = True,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        rows = await self.repository.optional_rows(
            statement_text,
            {"analysis_run_id": analysis_run_id, "limit": limit + 1},
        )
        if not rows:
            self.missing_sections.append(section_name)
        return bounded_items(
            f"sections.{section_name}",
            rows,
            limit,
            self.state,
            self.limits.max_text_length,
        )

    async def optional_signal_context_section(
        self,
        section_name: str,
        statement_text: str,
        signal: Signal,
        limit: int,
        included: bool = True,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        rows = await self.repository.optional_rows(
            statement_text,
            {
                "workspace_id": signal.workspace_id,
                "strategy_profile_key": signal.strategy_profile_key,
                "symbol_id": signal.symbol_id,
                "timeframe": signal.timeframe,
                "limit": limit + 1,
            },
        )
        if not rows:
            self.missing_sections.append(section_name)
        return bounded_items(
            f"sections.{section_name}",
            rows,
            limit,
            self.state,
            self.limits.max_text_length,
        )

    async def news_events(
        self,
        correlations: list[SignalNewsCorrelation],
    ) -> dict[UUID, NewsEvent]:
        events = await self.repository.list_news_events(
            [correlation.news_event_id for correlation in correlations]
        )
        return {event.id: event for event in events}

    def safe_sections(self, sections: dict[str, Any]) -> dict[str, Any]:
        result = safe_value(sections, self.state, "sections", self.limits.max_text_length)
        return result if isinstance(result, dict) else {}

    def signal_summary(self, signal: Signal | None, symbol: Symbol | None) -> dict[str, Any] | None:
        if signal is None:
            self.missing_sections.append("signalSummary")
            return None
        return {
            "signalId": signal.id,
            "analysisRunId": signal.analysis_run_id,
            "symbolId": signal.symbol_id,
            "symbol": symbol.symbol if symbol else None,
            "timeframe": signal.timeframe,
            "classificationStatus": signal.classification_status,
            "bias": signal.bias,
            "patternType": signal.pattern_type,
            "strategyProfileKey": signal.strategy_profile_key,
            "strategyProfileVersion": signal.strategy_profile_version,
            "confidenceScore": signal.confidence_score,
            "confidenceLabel": signal.confidence_label,
            "candidateStrength": signal.candidate_strength,
            "selectedPatternCandidateId": signal.selected_pattern_candidate_id,
            "movementDirection": signal.movement_direction,
            "movementQuality": signal.movement_quality,
            "volatilityState": signal.volatility_state,
            "trendState": signal.trend_state,
            "rangeState": signal.range_state,
            "noSignalReason": signal.no_signal_reason,
            "summary": signal.summary,
            "createdAt": signal.created_at,
        }

    def analysis_run_metadata(
        self,
        run: AnalysisRun | None,
        symbol: Symbol | None,
    ) -> dict[str, Any] | None:
        if run is None:
            self.missing_sections.append("analysisRunMetadata")
            return None
        return {
            "analysisRunId": run.id,
            "workspaceId": run.workspace_id,
            "userId": run.user_id,
            "symbolId": run.symbol_id,
            "symbol": symbol.symbol if symbol else None,
            "sourceId": run.source_id,
            "timeframe": run.timeframe,
            "startTime": run.start_time,
            "endTime": run.end_time,
            "warmupStartTime": run.warmup_start_time,
            "baselineStartTime": run.baseline_start_time,
            "analysisMode": run.analysis_mode,
            "status": run.status,
            "errorCode": run.error_code,
            "errorMessage": run.error_message,
            "engineVersion": run.engine_version,
            "ruleSetVersion": run.rule_set_version,
            "replayedFromAnalysisRunId": run.replayed_from_analysis_run_id,
            "replayMode": run.replay_mode,
            "createdAt": run.created_at,
            "startedAt": run.started_at,
            "completedAt": run.completed_at,
        }

    def market_context(self, signal: Signal, symbol: Symbol | None) -> dict[str, Any]:
        return {
            "symbolId": signal.symbol_id,
            "symbol": symbol.symbol if symbol else None,
            "displayName": symbol.display_name if symbol else None,
            "marketType": symbol.market_type if symbol else None,
            "baseAsset": symbol.base_asset if symbol else None,
            "quoteAsset": symbol.quote_asset if symbol else None,
            "timeframe": signal.timeframe,
            "pipSize": symbol.pip_size if symbol else None,
            "tickSize": symbol.tick_size if symbol else None,
        }

    def strategy_profile_section(
        self,
        signal: Signal,
        strategy_profile: StrategyProfile | None,
    ) -> dict[str, Any]:
        return {
            "signalSnapshot": signal.strategy_profile_snapshot_json,
            "registeredProfile": self.strategy_profile_row(strategy_profile),
        }

    def strategy_profile_row(self, profile: StrategyProfile | None) -> dict[str, Any] | None:
        if profile is None:
            return None
        return {
            "id": profile.id,
            "key": profile.key,
            "name": profile.name,
            "description": profile.description,
            "version": profile.version,
            "isActive": profile.is_active,
            "allowedPatterns": profile.allowed_patterns_json,
            "excludedPatterns": profile.excluded_patterns_json,
            "minimumCandidateStrength": profile.minimum_candidate_strength,
            "minimumConfidence": profile.minimum_confidence,
            "componentWeights": profile.component_weights_json,
            "riskFilters": profile.risk_filters_json,
            "noSignalRules": profile.no_signal_rules_json,
        }

    def candle_policy(self, run: AnalysisRun) -> dict[str, Any]:
        return {
            "includePartialLiveCandle": run.include_partial_live_candle,
            "usesFinalCandlesByDefault": not run.include_partial_live_candle,
            "startTime": run.start_time,
            "endTime": run.end_time,
            "warmupStartTime": run.warmup_start_time,
            "baselineStartTime": run.baseline_start_time,
            "rawFullCandleSeriesIncluded": False,
        }

    def source_metadata(self, source: DataSource | None) -> dict[str, Any]:
        if source is None:
            self.missing_sections.append("sourceMetadata")
            return {"present": False}
        return {
            "present": True,
            "sourceId": source.id,
            "workspaceId": source.workspace_id,
            "name": source.name,
            "sourceType": source.source_type,
            "provider": source.provider,
            "status": source.status,
            "config": source.config_json,
        }

    def feature_snapshot_section(self, snapshot: FeatureSnapshot | None) -> dict[str, Any]:
        return {
            "id": snapshot.id if snapshot else None,
            "createdAt": snapshot.created_at if snapshot else None,
            "summary": summarize_snapshot(
                "sections.featureSnapshotSummary",
                snapshot.features_json if snapshot else None,
                self.state,
                self.limits.max_text_length,
            ),
        }

    def indicator_snapshot_section(self, snapshot: IndicatorSnapshot | None) -> dict[str, Any]:
        return {
            "id": snapshot.id if snapshot else None,
            "createdAt": snapshot.created_at if snapshot else None,
            "summary": summarize_snapshot(
                "sections.indicatorSnapshotSummary",
                snapshot.indicators_json if snapshot else None,
                self.state,
                self.limits.max_text_length,
            ),
        }

    def deterministic_explanation_section(
        self,
        explanation: DeterministicExplanation | None,
    ) -> dict[str, Any]:
        if explanation is None:
            self.missing_sections.append("deterministicExplanation")
            return {"present": False}
        return {
            "present": True,
            "id": explanation.id,
            "templateVersion": explanation.template_version,
            "explanationType": explanation.explanation_type,
            "shortSummary": explanation.short_summary,
            "marketBehavior": explanation.market_behavior,
            "evidenceSummary": explanation.evidence_summary,
            "confidenceSummary": explanation.confidence_summary,
            "riskSummary": explanation.risk_summary,
            "noSignalSummary": explanation.no_signal_summary,
            "fullText": explanation.full_text,
            "sourceSnapshot": explanation.source_snapshot_json,
            "safetyStatus": explanation.safety_status,
            "blockedTerms": explanation.blocked_terms_json,
            "createdAt": explanation.created_at,
        }

    def llm_explanation_section(self, explanation: LlmExplanation | None) -> dict[str, Any]:
        if explanation is None:
            self.missing_sections.append("llmExplanation")
            return {"present": False}
        safe_output = (
            explanation.output_text
            if explanation.safety_status in {"passed", "fallback_used"}
            and explanation.grounding_status in {"grounded", "questionable", "not_checked"}
            else None
        )
        return {
            "present": True,
            "id": explanation.id,
            "provider": explanation.provider,
            "model": explanation.model,
            "promptVersion": explanation.prompt_version,
            "safetyStatus": explanation.safety_status,
            "groundingStatus": explanation.grounding_status,
            "blockedTerms": explanation.blocked_terms_json,
            "groundingIssues": explanation.grounding_issues_json,
            "tokensInput": explanation.tokens_input,
            "tokensOutput": explanation.tokens_output,
            "estimatedCost": explanation.estimated_cost,
            "errorMessage": explanation.error_message,
            "safeOutput": safe_output,
            "unsafeOutputRedacted": safe_output is None,
            "inputIncluded": False,
            "createdAt": explanation.created_at,
        }

    def news_correlation_section(
        self,
        correlations: list[SignalNewsCorrelation],
        news_events: dict[UUID, NewsEvent],
    ) -> dict[str, Any]:
        if not correlations:
            self.missing_sections.append("newsCorrelations")
        return bounded_items(
            "sections.newsCorrelations",
            [
                self.news_correlation_row(correlation, news_events.get(correlation.news_event_id))
                for correlation in correlations
            ],
            self.limits.max_news_correlations,
            self.state,
            self.limits.max_text_length,
        )

    def outcomes_section(self, outcomes: list[SignalOutcome], included: bool) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not outcomes:
            self.missing_sections.append("outcomes")
        return bounded_items(
            "sections.outcomes",
            [self.outcome_row(outcome) for outcome in outcomes],
            self.limits.max_outcomes,
            self.state,
            self.limits.max_text_length,
        )

    def reasoning_runs_section(
        self,
        runs: list[LlmReasoningRun],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not runs:
            self.missing_sections.append("reasoningRuns")
        return bounded_items(
            "sections.reasoningRuns",
            [self.reasoning_run_metadata(run) for run in runs],
            self.limits.max_scenarios,
            self.state,
            self.limits.max_text_length,
        )

    def action_plans_section(
        self,
        plans: list[ReasoningActionPlan],
        items: list[ReasoningActionItem],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not plans:
            self.missing_sections.append("actionPlans")
        return {
            "plans": bounded_items(
                "sections.actionPlans.plans",
                [self.action_plan_row(plan) for plan in plans],
                20,
                self.state,
                self.limits.max_text_length,
            ),
            "items": bounded_items(
                "sections.actionPlans.items",
                [self.action_item_row(item) for item in items],
                self.limits.max_action_items,
                self.state,
                self.limits.max_text_length,
            ),
        }

    def audit_section(self, logs: list[AnalysisAuditLog], included: bool) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not logs:
            self.missing_sections.append("auditTimeline")
        return bounded_items(
            "sections.auditTimeline",
            [self.audit_row(log) for log in logs],
            self.limits.max_audit_events,
            self.state,
            self.limits.max_text_length,
        )

    def screenshot_runs_section(
        self,
        runs: list[ChartScreenshotRun],
        included: bool,
    ) -> dict[str, Any]:
        if not included:
            return {"included": False}
        if not runs:
            self.missing_sections.append("screenshotArtifacts")
        return bounded_items(
            "sections.screenshotArtifacts",
            [self.chart_screenshot_row(run) for run in runs],
            20,
            self.state,
            self.limits.max_text_length,
        )

    def reproducibility_manifest(self, run: AnalysisRun) -> dict[str, Any]:
        return {
            "analysisMode": run.analysis_mode,
            "engineVersion": run.engine_version,
            "ruleSetVersion": run.rule_set_version,
            "engineSnapshot": run.engine_snapshot_json,
            "ruleSetSnapshot": run.rule_set_snapshot_json,
            "replayedFromAnalysisRunId": run.replayed_from_analysis_run_id,
            "replayMode": run.replay_mode,
        }

    def reasoning_safety_section(self, run: LlmReasoningRun) -> dict[str, Any]:
        return {
            "status": run.status,
            "safetyStatus": run.safety_status,
            "groundingStatus": run.grounding_status,
            "blockedTerms": run.blocked_terms_json,
            "groundingIssues": run.grounding_issues_json,
        }

    def parser_extraction_metadata(self, run: ChartScreenshotRun) -> dict[str, Any]:
        return {
            "parserName": run.parser_name,
            "parserVersion": run.parser_version,
            "parserSourcePath": run.parser_source_path,
            "chartType": run.chart_type,
            "supportedForAnalysis": run.supported_for_analysis,
            "analysisBlockedReason": run.analysis_blocked_reason,
            "extractionConfidence": run.extraction_confidence,
            "rawCandleCount": run.raw_candle_count,
            "storedCandleCount": run.stored_candle_count,
            "duplicateCount": run.duplicate_count,
            "conflictCount": run.conflict_count,
            "rawImageBytesIncluded": False,
            "rawFullOcrPayloadIncluded": False,
            "rawFullCandleSeriesIncluded": False,
        }

    def review_correction_state(self, run: ChartScreenshotRun) -> dict[str, Any]:
        return {
            "status": run.status,
            "humanReview": run.parser_metadata_json.get("humanReview"),
            "correctedFromRunId": run.parser_metadata_json.get("correctedFromChartScreenshotRunId"),
            "lastErrorCode": run.last_error_code,
            "lastErrorMessage": run.last_error_message,
        }

    def evidence_row(self, item: SignalEvidence) -> dict[str, Any]:
        return {
            "id": item.id,
            "evidenceType": item.evidence_type,
            "direction": item.direction,
            "message": item.message,
            "numericValue": item.numeric_value,
            "weight": item.weight,
            "metadata": item.metadata_json,
            "createdAt": item.created_at,
        }

    def confidence_component_row(self, item: SignalConfidenceComponent) -> dict[str, Any]:
        return {
            "id": item.id,
            "componentName": item.component_name,
            "componentScore": item.component_score,
            "componentWeight": item.component_weight,
            "weightedScore": item.weighted_score,
            "reason": item.reason,
            "createdAt": item.created_at,
        }

    def risk_note_row(self, item: SignalRiskNote) -> dict[str, Any]:
        return {
            "id": item.id,
            "code": item.code,
            "severity": item.severity,
            "message": item.message,
            "metadata": item.metadata_json,
            "createdAt": item.created_at,
        }

    def pattern_candidate_row(self, candidate: PatternCandidate | None) -> dict[str, Any] | None:
        if candidate is None:
            return None
        return {
            "id": candidate.id,
            "analysisRunId": candidate.analysis_run_id,
            "patternType": candidate.pattern_type,
            "bias": candidate.bias,
            "strengthScore": candidate.strength_score,
            "isSelected": candidate.is_selected,
            "evidence": candidate.evidence_json,
            "riskNotes": candidate.risk_notes_json,
            "metrics": candidate.metrics_json,
            "createdAt": candidate.created_at,
        }

    def news_correlation_row(
        self,
        correlation: SignalNewsCorrelation,
        event: NewsEvent | None,
    ) -> dict[str, Any]:
        return {
            "id": correlation.id,
            "newsEventId": correlation.news_event_id,
            "eventTitle": event.title if event else None,
            "eventTime": event.event_time if event else None,
            "eventType": event.event_type if event else None,
            "importance": event.importance if event else None,
            "sentiment": event.sentiment if event else None,
            "currency": event.currency if event else None,
            "asset": event.asset if event else None,
            "correlationScore": correlation.correlation_score,
            "correlationLabel": correlation.correlation_label,
            "directionAlignment": correlation.direction_alignment,
            "volatilityReaction": correlation.volatility_reaction,
            "timeDeltaMinutes": correlation.time_delta_minutes,
            "reason": correlation.reason,
            "metadata": correlation.metadata_json,
            "createdAt": correlation.created_at,
        }

    def outcome_row(self, outcome: SignalOutcome) -> dict[str, Any]:
        return {
            "id": outcome.id,
            "analysisRunId": outcome.analysis_run_id,
            "signalId": outcome.signal_id,
            "symbolId": outcome.symbol_id,
            "timeframe": outcome.timeframe,
            "strategyProfileKey": outcome.strategy_profile_key,
            "strategyProfileVersion": outcome.strategy_profile_version,
            "patternType": outcome.pattern_type,
            "bias": outcome.bias,
            "classificationStatus": outcome.classification_status,
            "horizonMinutes": outcome.horizon_minutes,
            "evaluationStatus": outcome.evaluation_status,
            "referenceTime": outcome.reference_time,
            "referencePrice": outcome.reference_price,
            "futureWindowStart": outcome.future_window_start,
            "futureWindowEnd": outcome.future_window_end,
            "futureCandleCount": outcome.future_candle_count,
            "maxFavorableMove": outcome.max_favorable_move,
            "maxAdverseMove": outcome.max_adverse_move,
            "netMove": outcome.net_move,
            "directionFollowed": outcome.direction_followed,
            "reversalDetected": outcome.reversal_detected,
            "outcomeLabel": outcome.outcome_label,
            "movementQuality": outcome.movement_quality,
            "evaluationVersion": outcome.evaluation_version,
            "metadata": outcome.metadata_json,
            "createdAt": outcome.created_at,
        }

    def reasoning_run_metadata(self, run: LlmReasoningRun) -> dict[str, Any]:
        output_summary = None
        if run.safety_status in {"passed", "fallback_used"} and isinstance(run.output_json, dict):
            output_summary = run.output_json.get("summary")
        return {
            "reasoningRunId": run.id,
            "workspaceId": run.workspace_id,
            "analysisRunId": run.analysis_run_id,
            "signalId": run.signal_id,
            "outcomeId": run.outcome_id,
            "sourceType": run.source_type,
            "provider": run.provider,
            "model": run.model,
            "promptVersion": run.prompt_version,
            "reasoningType": run.reasoning_type,
            "status": run.status,
            "safetyStatus": run.safety_status,
            "groundingStatus": run.grounding_status,
            "outputSummary": output_summary,
            "outputIncluded": False,
            "createdAt": run.created_at,
            "updatedAt": run.updated_at,
        }

    def scenario_row(self, scenario: ScenarioHypothesis) -> dict[str, Any]:
        return {
            "id": scenario.id,
            "reasoningRunId": scenario.reasoning_run_id,
            "scenarioType": scenario.scenario_type,
            "scenarioLabel": scenario.scenario_label,
            "possibilityLabel": scenario.possibility_label,
            "supportingEvidence": scenario.supporting_evidence_json,
            "conflictingEvidence": scenario.conflicting_evidence_json,
            "outcomeHistory": scenario.outcome_history_json,
            "nextObservations": scenario.next_observations_json,
            "suggestedBackendActions": scenario.suggested_backend_actions_json,
            "riskNotes": scenario.risk_notes_json,
            "sortOrder": scenario.sort_order,
            "createdAt": scenario.created_at,
        }

    def action_plan_row(self, plan: ReasoningActionPlan) -> dict[str, Any]:
        return {
            "id": plan.id,
            "sourceType": plan.source_type,
            "sourceId": plan.source_id,
            "signalId": plan.signal_id,
            "analysisRunId": plan.analysis_run_id,
            "reasoningRunId": plan.reasoning_run_id,
            "status": plan.status,
            "planVersion": plan.plan_version,
            "createdFrom": plan.created_from,
            "summary": plan.summary,
            "metadata": plan.metadata_json,
            "createdAt": plan.created_at,
            "updatedAt": plan.updated_at,
        }

    def action_item_row(self, item: ReasoningActionItem) -> dict[str, Any]:
        return {
            "id": item.id,
            "actionPlanId": item.action_plan_id,
            "sourceType": item.source_type,
            "sourceId": item.source_id,
            "signalId": item.signal_id,
            "analysisRunId": item.analysis_run_id,
            "reasoningRunId": item.reasoning_run_id,
            "actionType": item.action_type,
            "status": item.status,
            "priority": item.priority,
            "dueAt": item.due_at,
            "horizonMinutes": item.horizon_minutes,
            "input": item.input_json,
            "result": item.result_json,
            "errorCode": item.error_code,
            "errorMessage": item.error_message,
            "attempts": item.attempts,
            "maxAttempts": item.max_attempts,
            "completedAt": item.completed_at,
        }

    def audit_row(self, log: AnalysisAuditLog) -> dict[str, Any]:
        return {
            "id": log.id,
            "analysisRunId": log.analysis_run_id,
            "eventType": log.event_type,
            "message": log.message,
            "metadata": log.metadata_json,
            "createdAt": log.created_at,
        }

    def chart_screenshot_row(self, run: ChartScreenshotRun) -> dict[str, Any]:
        return {
            "chartScreenshotRunId": run.id,
            "workspaceId": run.workspace_id,
            "userId": run.user_id,
            "sourceId": run.source_id,
            "symbolId": run.symbol_id,
            "analysisRunId": run.analysis_run_id,
            "timeframe": run.timeframe,
            "fileName": run.file_name,
            "parserName": run.parser_name,
            "parserVersion": run.parser_version,
            "status": run.status,
            "extractionConfidence": run.extraction_confidence,
            "analysisHypothesis": run.analysis_hypothesis,
            "analysisHypothesisConfidence": run.analysis_hypothesis_confidence,
            "extractedWindowStart": run.extracted_window_start,
            "extractedWindowEnd": run.extracted_window_end,
            "createdAt": run.created_at,
            "completedAt": run.completed_at,
        }

    def replay_row(self, run: AnalysisRun) -> dict[str, Any]:
        return {
            "analysisRunId": run.id,
            "status": run.status,
            "engineVersion": run.engine_version,
            "ruleSetVersion": run.rule_set_version,
            "replayedFromAnalysisRunId": run.replayed_from_analysis_run_id,
            "replayMode": run.replay_mode,
            "createdAt": run.created_at,
            "completedAt": run.completed_at,
        }
