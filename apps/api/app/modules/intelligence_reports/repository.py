from typing import Any
from uuid import UUID

from sqlalchemy import Select, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import TextClause

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.candles.models import Candle
from app.modules.chart_screenshots.models import ChartScreenshotRun
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
from app.modules.symbols.models import Symbol


class IntelligenceReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_confidence_components(
        self,
        signal_id: UUID,
    ) -> list[SignalConfidenceComponent]:
        statement: Select[tuple[SignalConfidenceComponent]] = (
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_evidence(self, signal_id: UUID) -> list[SignalEvidence]:
        statement: Select[tuple[SignalEvidence]] = (
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_risk_notes(self, signal_id: UUID) -> list[SignalRiskNote]:
        statement: Select[tuple[SignalRiskNote]] = (
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_deterministic_explanation_by_signal_id(
        self,
        signal_id: UUID,
    ) -> DeterministicExplanation | None:
        statement: Select[tuple[DeterministicExplanation]] = select(
            DeterministicExplanation
        ).where(DeterministicExplanation.signal_id == signal_id)
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

    async def get_llm_explanation_by_signal_id(self, signal_id: UUID) -> LlmExplanation | None:
        statement: Select[tuple[LlmExplanation]] = (
            select(LlmExplanation)
            .where(LlmExplanation.signal_id == signal_id)
            .order_by(LlmExplanation.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_news_correlations_by_signal_id(
        self,
        signal_id: UUID,
    ) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_correlations_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.analysis_run_id == analysis_run_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
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

    async def get_latest_reasoning_run_by_signal_id(
        self,
        signal_id: UUID,
    ) -> LlmReasoningRun | None:
        statement: Select[tuple[LlmReasoningRun]] = (
            select(LlmReasoningRun)
            .where(LlmReasoningRun.signal_id == signal_id)
            .order_by(LlmReasoningRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return await self.session.get(LlmReasoningRun, reasoning_run_id)

    async def list_scenario_hypotheses(
        self,
        reasoning_run_id: UUID,
    ) -> list[ScenarioHypothesis]:
        statement: Select[tuple[ScenarioHypothesis]] = (
            select(ScenarioHypothesis)
            .where(ScenarioHypothesis.reasoning_run_id == reasoning_run_id)
            .order_by(ScenarioHypothesis.sort_order.asc(), ScenarioHypothesis.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_action_plan_by_reasoning_run_id(
        self,
        reasoning_run_id: UUID,
    ) -> ReasoningActionPlan | None:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.reasoning_run_id == reasoning_run_id)
            .order_by(ReasoningActionPlan.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_action_plan_by_signal_id(
        self,
        signal_id: UUID,
    ) -> ReasoningActionPlan | None:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.signal_id == signal_id)
            .order_by(ReasoningActionPlan.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_action_plan_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> ReasoningActionPlan | None:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.analysis_run_id == analysis_run_id)
            .order_by(ReasoningActionPlan.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_action_items(
        self,
        action_plan_id: UUID,
    ) -> list[ReasoningActionItem]:
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(ReasoningActionItem.action_plan_id == action_plan_id)
            .order_by(ReasoningActionItem.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_signal_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_analysis_outcomes(self, analysis_run_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.analysis_run_id == analysis_run_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        return await self.session.get(SignalOutcome, outcome_id)

    async def list_historical_outcomes(
        self,
        workspace_id: UUID,
        horizon_minutes: int,
        symbol_id: UUID | None = None,
        timeframe: str | None = None,
        pattern_type: str | None = None,
        strategy_profile_key: str | None = None,
        limit: int = 1000,
    ) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.horizon_minutes == horizon_minutes,
            )
            .order_by(SignalOutcome.reference_time.desc())
            .limit(limit)
        )
        if symbol_id is not None:
            statement = statement.where(SignalOutcome.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(SignalOutcome.timeframe == timeframe)
        if pattern_type is not None:
            statement = statement.where(SignalOutcome.pattern_type == pattern_type)
        if strategy_profile_key is not None:
            statement = statement.where(SignalOutcome.strategy_profile_key == strategy_profile_key)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

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

    async def list_pattern_candidates(self, analysis_run_id: UUID) -> list[PatternCandidate]:
        statement: Select[tuple[PatternCandidate]] = (
            select(PatternCandidate)
            .where(PatternCandidate.analysis_run_id == analysis_run_id)
            .order_by(PatternCandidate.is_selected.desc(), PatternCandidate.strength_score.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_audit_logs(self, analysis_run_id: UUID) -> list[AnalysisAuditLog]:
        statement: Select[tuple[AnalysisAuditLog]] = (
            select(AnalysisAuditLog)
            .where(AnalysisAuditLog.analysis_run_id == analysis_run_id)
            .order_by(AnalysisAuditLog.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_candles_for_run(self, run: AnalysisRun) -> int:
        statement = (
            select(Candle)
            .where(
                Candle.workspace_id == run.workspace_id,
                Candle.symbol_id == run.symbol_id,
                Candle.timeframe == run.timeframe,
                Candle.timestamp >= run.start_time,
                Candle.timestamp <= run.end_time,
                Candle.is_final.is_(True),
            )
        )
        if run.source_id is not None:
            statement = statement.where(Candle.source_id == run.source_id)
        result = await self.session.execute(statement)
        return len(list(result.scalars().all()))

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
            "continuation_count, partial_follow_through_count, no_follow_through_count, "
            "reversal_count, insufficient_data_count, continuation_rate, reversal_rate, "
            "no_follow_through_rate, confidence_alignment_score, diagnostic_label, "
            "diagnostic_summary, metadata_json, created_at "
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
            "timeframe, horizon_minutes, sample_size, evaluated_count, continuation_rate, "
            "reversal_rate, no_follow_through_rate, confidence_alignment_score, "
            "diagnostic_label, diagnostic_summary, metadata_json, created_at "
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
            "strategy_profile_version, pattern_type, symbol_id, timeframe, horizon_minutes, "
            "severity, status, title, rationale, suggested_change_json, evidence_json, "
            "created_at, updated_at "
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

    async def list_chart_screenshot_runs_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> list[ChartScreenshotRun]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.analysis_run_id == analysis_run_id)
            .order_by(ChartScreenshotRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_chart_screenshot_run(self, decision_id: UUID) -> ChartScreenshotRun | None:
        return await self.session.get(ChartScreenshotRun, decision_id)

    async def list_chart_corrections(self, run_id: UUID) -> list[ChartScreenshotRun]:
        statement: Select[tuple[ChartScreenshotRun]] = (
            select(ChartScreenshotRun)
            .where(ChartScreenshotRun.parser_source_path == f"correction:{run_id}")
            .order_by(ChartScreenshotRun.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
