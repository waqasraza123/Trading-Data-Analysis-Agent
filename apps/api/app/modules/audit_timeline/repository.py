from typing import Any
from uuid import UUID

from sqlalchemy import Select, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
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


class AuditTimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return await self.session.get(LlmReasoningRun, reasoning_run_id)

    async def get_action_plan(self, action_plan_id: UUID) -> ReasoningActionPlan | None:
        return await self.session.get(ReasoningActionPlan, action_plan_id)

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        return await self.session.get(SignalOutcome, outcome_id)

    async def get_chart_screenshot_run(self, run_id: UUID) -> ChartScreenshotRun | None:
        return await self.session.get(ChartScreenshotRun, run_id)

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        statement: Select[tuple[FeatureSnapshot]] = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_indicator_snapshot(self, analysis_run_id: UUID) -> IndicatorSnapshot | None:
        statement: Select[tuple[IndicatorSnapshot]] = (
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.analysis_run_id == analysis_run_id)
            .order_by(IndicatorSnapshot.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_pattern_candidate(self, pattern_candidate_id: UUID) -> PatternCandidate | None:
        return await self.session.get(PatternCandidate, pattern_candidate_id)

    async def list_pattern_candidates(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[PatternCandidate]:
        statement: Select[tuple[PatternCandidate]] = (
            select(PatternCandidate)
            .where(PatternCandidate.analysis_run_id == analysis_run_id)
            .order_by(PatternCandidate.is_selected.desc(), PatternCandidate.strength_score.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_confidence_components(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[SignalConfidenceComponent]:
        statement: Select[tuple[SignalConfidenceComponent]] = (
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_evidence(self, signal_id: UUID, limit: int) -> list[SignalEvidence]:
        statement: Select[tuple[SignalEvidence]] = (
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_risk_notes(self, signal_id: UUID, limit: int) -> list[SignalRiskNote]:
        statement: Select[tuple[SignalRiskNote]] = (
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_deterministic_explanation_by_signal_id(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = (
            select(DeterministicExplanation)
            .where(DeterministicExplanation.signal_id == signal_id)
            .order_by(DeterministicExplanation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_deterministic_explanation_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = (
            select(DeterministicExplanation)
            .where(DeterministicExplanation.analysis_run_id == analysis_run_id)
            .order_by(DeterministicExplanation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_llm_explanations_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[LlmExplanation]:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.signal_id == signal_id)
            .order_by(LlmExplanation.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_llm_explanations_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[LlmExplanation]:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.analysis_run_id == analysis_run_id)
            .order_by(LlmExplanation.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_correlations_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_correlations_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.analysis_run_id == analysis_run_id)
            .order_by(SignalNewsCorrelation.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_events(self, news_event_ids: list[UUID]) -> list[NewsEvent]:
        if not news_event_ids:
            return []
        statement: Select[tuple[NewsEvent]] = select(NewsEvent).where(
            NewsEvent.id.in_(news_event_ids)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_signal_outcomes(self, signal_id: UUID, limit: int) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_analysis_outcomes(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.analysis_run_id == analysis_run_id)
            .order_by(SignalOutcome.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_reasoning_runs_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[LlmReasoningRun]:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.signal_id == signal_id)
            .order_by(LlmReasoningRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_reasoning_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[LlmReasoningRun]:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.analysis_run_id == analysis_run_id)
            .order_by(LlmReasoningRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_reasoning_runs_by_outcome_id(
        self,
        outcome_id: UUID,
        limit: int,
    ) -> list[LlmReasoningRun]:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.outcome_id == outcome_id)
            .order_by(LlmReasoningRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_scenario_hypotheses(
        self,
        reasoning_run_id: UUID,
        limit: int,
    ) -> list[ScenarioHypothesis]:
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id == reasoning_run_id)
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[ReasoningActionPlan]:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.signal_id == signal_id)
            .order_by(ReasoningActionPlan.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[ReasoningActionPlan]:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.analysis_run_id == analysis_run_id)
            .order_by(ReasoningActionPlan.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans_by_reasoning_run_id(
        self,
        reasoning_run_id: UUID,
        limit: int,
    ) -> list[ReasoningActionPlan]:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.reasoning_run_id == reasoning_run_id)
            .order_by(ReasoningActionPlan.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_items(
        self,
        action_plan_id: UUID,
        limit: int,
    ) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(ReasoningActionItem.action_plan_id == action_plan_id)
            .order_by(ReasoningActionItem.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_items_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(ReasoningActionItem.signal_id == signal_id)
            .order_by(ReasoningActionItem.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_chart_screenshot_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[ChartScreenshotRun]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.analysis_run_id == analysis_run_id)
            .order_by(ChartScreenshotRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_chart_corrections(
        self,
        run_id: UUID,
        limit: int,
    ) -> list[ChartScreenshotRun]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.parser_source_path == f"correction:{run_id}")
            .order_by(ChartScreenshotRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_scheduled_scan_items_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[ScheduledScanRunItem]:
        statement: Select[tuple[ScheduledScanRunItem]] = (
            select(ScheduledScanRunItem)
            .where(ScheduledScanRunItem.analysis_run_id == analysis_run_id)
            .order_by(ScheduledScanRunItem.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_scheduled_scan_runs_by_item_ids(
        self,
        scan_run_ids: list[UUID],
        limit: int,
    ) -> list[ScheduledScanRun]:
        if not scan_run_ids:
            return []
        statement: Select[tuple[ScheduledScanRun]] = (
            select(ScheduledScanRun)
            .where(ScheduledScanRun.id.in_(scan_run_ids))
            .order_by(ScheduledScanRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_quality_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[IntelligenceQualityRun]:
        statement: Select[tuple[IntelligenceQualityRun]] = (
            select(IntelligenceQualityRun)
            .where(IntelligenceQualityRun.analysis_run_id == analysis_run_id)
            .order_by(IntelligenceQualityRun.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_quality_runs_by_signal_id(
        self,
        signal_id: UUID,
        limit: int,
    ) -> list[IntelligenceQualityRun]:
        statement: Select[tuple[IntelligenceQualityRun]] = (
            select(IntelligenceQualityRun)
            .where(IntelligenceQualityRun.signal_id == signal_id)
            .order_by(IntelligenceQualityRun.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_quality_findings_by_run_ids(
        self,
        quality_run_ids: list[UUID],
        limit: int,
    ) -> list[IntelligenceQualityFinding]:
        if not quality_run_ids:
            return []
        statement: Select[tuple[IntelligenceQualityFinding]] = (
            select(IntelligenceQualityFinding)
            .where(IntelligenceQualityFinding.quality_run_id.in_(quality_run_ids))
            .order_by(IntelligenceQualityFinding.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_shadow_results_by_quality_run_ids(
        self,
        quality_run_ids: list[UUID],
        limit: int,
    ) -> list[ShadowClassificationResult]:
        if not quality_run_ids:
            return []
        statement: Select[tuple[ShadowClassificationResult]] = (
            select(ShadowClassificationResult)
            .where(ShadowClassificationResult.quality_run_id.in_(quality_run_ids))
            .order_by(ShadowClassificationResult.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_replay_runs(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[AnalysisRun]:
        statement: Select[tuple[AnalysisRun]] = (
            select(AnalysisRun)
            .where(AnalysisRun.replayed_from_analysis_run_id == analysis_run_id)
            .order_by(AnalysisRun.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_audit_logs(
        self,
        analysis_run_id: UUID,
        limit: int,
    ) -> list[AnalysisAuditLog]:
        statement: Select[tuple[AnalysisAuditLog]] = (
            select(AnalysisAuditLog)
            .where(AnalysisAuditLog.analysis_run_id == analysis_run_id)
            .order_by(AnalysisAuditLog.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_optional_strategy_profile_diagnostics(
        self,
        workspace_id: UUID,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = text(
            "select id, diagnostic_run_id, strategy_profile_key, strategy_profile_version, "
            "symbol_id, timeframe, horizon_minutes, sample_size, evaluated_count, "
            "diagnostic_label, diagnostic_summary, metadata_json, created_at "
            "from strategy_profile_diagnostics "
            "where workspace_id = :workspace_id "
            "and (:strategy_profile_key is null or strategy_profile_key = :strategy_profile_key) "
            "and (:symbol_id is null or symbol_id = :symbol_id) "
            "and (:timeframe is null or timeframe = :timeframe) "
            "order by created_at desc limit :limit"
        )
        return await self.fetch_optional_rows(
            statement,
            {
                "workspace_id": workspace_id,
                "strategy_profile_key": strategy_profile_key,
                "symbol_id": symbol_id,
                "timeframe": timeframe,
                "limit": limit,
            },
        )

    async def list_optional_pattern_diagnostics(
        self,
        workspace_id: UUID,
        pattern_type: str | None,
        strategy_profile_key: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = text(
            "select id, diagnostic_run_id, pattern_type, strategy_profile_key, symbol_id, "
            "timeframe, horizon_minutes, sample_size, evaluated_count, diagnostic_label, "
            "diagnostic_summary, metadata_json, created_at "
            "from pattern_outcome_diagnostics "
            "where workspace_id = :workspace_id "
            "and (:pattern_type is null or pattern_type = :pattern_type) "
            "and (:strategy_profile_key is null or strategy_profile_key = :strategy_profile_key) "
            "and (:symbol_id is null or symbol_id = :symbol_id) "
            "and (:timeframe is null or timeframe = :timeframe) "
            "order by created_at desc limit :limit"
        )
        return await self.fetch_optional_rows(
            statement,
            {
                "workspace_id": workspace_id,
                "pattern_type": pattern_type,
                "strategy_profile_key": strategy_profile_key,
                "symbol_id": symbol_id,
                "timeframe": timeframe,
                "limit": limit,
            },
        )

    async def list_optional_calibration_recommendations(
        self,
        workspace_id: UUID,
        strategy_profile_key: str | None,
        pattern_type: str | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = text(
            "select id, diagnostic_run_id, recommendation_type, strategy_profile_key, "
            "pattern_type, symbol_id, timeframe, horizon_minutes, severity, status, title, "
            "rationale, suggested_change_json, evidence_json, created_at, updated_at "
            "from calibration_recommendations "
            "where workspace_id = :workspace_id "
            "and (:strategy_profile_key is null or strategy_profile_key = :strategy_profile_key) "
            "and (:pattern_type is null or pattern_type = :pattern_type) "
            "and (:symbol_id is null or symbol_id = :symbol_id) "
            "and (:timeframe is null or timeframe = :timeframe) "
            "order by created_at desc limit :limit"
        )
        return await self.fetch_optional_rows(
            statement,
            {
                "workspace_id": workspace_id,
                "strategy_profile_key": strategy_profile_key,
                "pattern_type": pattern_type,
                "symbol_id": symbol_id,
                "timeframe": timeframe,
                "limit": limit,
            },
        )

    async def list_optional_action_worker_runs(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[dict[str, Any]]:
        statement = text(
            "select id, worker_id, status, batch_limit, claimed_count, completed_count, "
            "skipped_count, failed_count, started_at, completed_at, error_message, "
            "metadata_json, created_at "
            "from reasoning_action_worker_runs "
            "where workspace_id = :workspace_id or workspace_id is null "
            "order by created_at desc limit :limit"
        )
        return await self.fetch_optional_rows(
            statement,
            {"workspace_id": workspace_id, "limit": limit},
        )

    async def fetch_optional_rows(
        self,
        statement: TextClause,
        parameters: dict[str, object],
    ) -> list[dict[str, Any]]:
        try:
            result = await self.session.execute(statement, parameters)
        except SQLAlchemyError:
            return []
        return [dict(row) for row in result.mappings().all()]
