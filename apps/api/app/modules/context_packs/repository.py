from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.action_plans.models import ReasoningActionItem, ReasoningActionPlan
from app.modules.analysis.models import AnalysisAuditLog, AnalysisRun
from app.modules.candles.models import Candle
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


class ContextPackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_reasoning_run(self, reasoning_run_id: UUID) -> LlmReasoningRun | None:
        return await self.session.get(LlmReasoningRun, reasoning_run_id)

    async def get_outcome(self, outcome_id: UUID) -> SignalOutcome | None:
        return await self.session.get(SignalOutcome, outcome_id)

    async def get_chart_screenshot_run(self, run_id: UUID) -> ChartScreenshotRun | None:
        return await self.session.get(ChartScreenshotRun, run_id)

    async def get_symbol(self, symbol_id: UUID) -> Symbol | None:
        return await self.session.get(Symbol, symbol_id)

    async def get_data_source(self, source_id: UUID | None) -> DataSource | None:
        if source_id is None:
            return None
        return await self.session.get(DataSource, source_id)

    async def get_strategy_profile(
        self,
        key: str | None,
        version: str | None,
    ) -> StrategyProfile | None:
        if key is None or version is None:
            return None
        statement: Select[tuple[StrategyProfile]] = (
            select(StrategyProfile)
            .where(StrategyProfile.key == key, StrategyProfile.version == version)
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

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

    async def get_selected_pattern_candidate(self, signal: Signal) -> PatternCandidate | None:
        if signal.selected_pattern_candidate_id is not None:
            candidate = await self.session.get(PatternCandidate, signal.selected_pattern_candidate_id)
            if candidate is not None:
                return candidate
        statement: Select[tuple[PatternCandidate]] = (
            select(PatternCandidate)
            .where(PatternCandidate.analysis_run_id == signal.analysis_run_id)
            .order_by(PatternCandidate.is_selected.desc(), PatternCandidate.strength_score.desc())
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

    async def list_evidence(self, signal_id: UUID, limit: int) -> list[SignalEvidence]:
        statement: Select[tuple[SignalEvidence]] = (
            select(SignalEvidence)
            .where(SignalEvidence.signal_id == signal_id)
            .order_by(SignalEvidence.created_at.asc())
            .limit(limit + 1)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_confidence_components(self, signal_id: UUID) -> list[SignalConfidenceComponent]:
        statement: Select[tuple[SignalConfidenceComponent]] = (
            select(SignalConfidenceComponent)
            .where(SignalConfidenceComponent.signal_id == signal_id)
            .order_by(SignalConfidenceComponent.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_risk_notes(self, signal_id: UUID, limit: int) -> list[SignalRiskNote]:
        statement: Select[tuple[SignalRiskNote]] = (
            select(SignalRiskNote)
            .where(SignalRiskNote.signal_id == signal_id)
            .order_by(SignalRiskNote.created_at.asc())
            .limit(limit + 1)
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
        limit: int,
    ) -> list[SignalNewsCorrelation]:
        statement: Select[tuple[SignalNewsCorrelation]] = (
            select(SignalNewsCorrelation)
            .where(SignalNewsCorrelation.signal_id == signal_id)
            .order_by(SignalNewsCorrelation.correlation_score.desc())
            .limit(limit + 1)
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
            .order_by(SignalNewsCorrelation.correlation_score.desc())
            .limit(limit + 1)
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
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
            .limit(limit + 1)
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
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.asc())
            .limit(limit + 1)
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
            .order_by(LlmReasoningRun.created_at.desc())
            .limit(limit + 1)
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
            .limit(limit + 1)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans_by_signal_id(
        self,
        signal_id: UUID,
    ) -> list[ReasoningActionPlan]:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.signal_id == signal_id)
            .order_by(ReasoningActionPlan.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans_by_analysis_run_id(
        self,
        analysis_run_id: UUID,
    ) -> list[ReasoningActionPlan]:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.analysis_run_id == analysis_run_id)
            .order_by(ReasoningActionPlan.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_plans_by_reasoning_run_id(
        self,
        reasoning_run_id: UUID,
    ) -> list[ReasoningActionPlan]:
        statement: Select[tuple[ReasoningActionPlan]] = (
            select(ReasoningActionPlan)
            .where(ReasoningActionPlan.reasoning_run_id == reasoning_run_id)
            .order_by(ReasoningActionPlan.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_action_items(
        self,
        action_plan_ids: list[UUID],
        limit: int,
    ) -> list[ReasoningActionItem]:
        if not action_plan_ids:
            return []
        statement: Select[tuple[ReasoningActionItem]] = (
            select(ReasoningActionItem)
            .where(ReasoningActionItem.action_plan_id.in_(action_plan_ids))
            .order_by(ReasoningActionItem.created_at.asc())
            .limit(limit + 1)
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
            .limit(limit + 1)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

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

    async def list_replay_links(self, analysis_run_id: UUID) -> list[AnalysisRun]:
        statement: Select[tuple[AnalysisRun]] = (
            select(AnalysisRun)
            .where(AnalysisRun.replayed_from_analysis_run_id == analysis_run_id)
            .order_by(AnalysisRun.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count_final_candles_for_run(self, run: AnalysisRun) -> int:
        statement = select(func.count()).select_from(Candle).where(
            Candle.workspace_id == run.workspace_id,
            Candle.symbol_id == run.symbol_id,
            Candle.timeframe == run.timeframe,
            Candle.timestamp >= run.start_time,
            Candle.timestamp <= run.end_time,
            Candle.is_final.is_(True),
        )
        if run.source_id is not None:
            statement = statement.where(Candle.source_id == run.source_id)
        result = await self.session.execute(statement)
        return int(result.scalar_one())

    async def optional_rows(
        self,
        statement_text: str,
        parameters: dict[str, object],
    ) -> list[dict[str, Any]]:
        try:
            result = await self.session.execute(text(statement_text), parameters)
        except SQLAlchemyError:
            await self.session.rollback()
            return []
        return [dict(row) for row in result.mappings().all()]
