from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advanced_features.models import AdvancedFeatureSnapshot
from app.modules.analysis.models import AnalysisRun
from app.modules.candles.models import Candle
from app.modules.cross_asset_context.models import CrossAssetContextResult, CrossAssetContextRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.decision_readiness.models import DecisionReadinessAssessment
from app.modules.features.models import FeatureSnapshot
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.patterns.models import PatternCandidate
from app.modules.setup_context.models import SetupContext
from app.modules.signals.models import (
    Signal,
    SignalConfidenceComponent,
    SignalEvidence,
    SignalRiskNote,
)
from app.modules.timeframe_aggregation.models import MultiTimeframeContext


class SetupContextRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_signal(self, signal_id: UUID) -> Signal | None:
        return await self.session.get(Signal, signal_id)

    async def get_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return await self.session.get(AnalysisRun, analysis_run_id)

    async def get_signal_by_analysis_run_id(self, analysis_run_id: UUID) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(Signal.analysis_run_id == analysis_run_id)
            .order_by(Signal.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_by_signal_version(
        self,
        signal_id: UUID,
        context_version: str,
    ) -> SetupContext | None:
        statement: Select[tuple[SetupContext]] = select(SetupContext).where(
            SetupContext.signal_id == signal_id,
            SetupContext.context_version == context_version,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_for_signal(self, signal_id: UUID) -> SetupContext | None:
        statement: Select[tuple[SetupContext]] = (
            select(SetupContext)
            .where(SetupContext.signal_id == signal_id)
            .order_by(SetupContext.updated_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_for_analysis_run(self, analysis_run_id: UUID) -> SetupContext | None:
        statement: Select[tuple[SetupContext]] = (
            select(SetupContext)
            .where(SetupContext.analysis_run_id == analysis_run_id)
            .order_by(SetupContext.updated_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        setup_context: SetupContext,
        existing: SetupContext | None,
        force_recompute: bool,
    ) -> SetupContext:
        if existing is not None and not force_recompute:
            return existing
        if existing is None:
            self.session.add(setup_context)
            await self.session.flush()
            await self.session.refresh(setup_context)
            return setup_context
        copy_setup_context_values(setup_context, existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

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

    async def get_feature_snapshot(self, analysis_run_id: UUID) -> FeatureSnapshot | None:
        statement: Select[tuple[FeatureSnapshot]] = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_advanced_feature_snapshot(
        self,
        analysis_run_id: UUID,
    ) -> AdvancedFeatureSnapshot | None:
        statement: Select[tuple[AdvancedFeatureSnapshot]] = (
            select(AdvancedFeatureSnapshot)
            .where(AdvancedFeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(AdvancedFeatureSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_selected_pattern_candidate(self, signal: Signal) -> PatternCandidate | None:
        if signal.selected_pattern_candidate_id is None:
            return None
        return await self.session.get(PatternCandidate, signal.selected_pattern_candidate_id)

    async def get_market_regime(
        self,
        analysis_run_id: UUID,
        signal_id: UUID,
    ) -> MarketRegimeContext | None:
        statement: Select[tuple[MarketRegimeContext]] = (
            select(MarketRegimeContext)
            .where(
                or_(
                    MarketRegimeContext.signal_id == signal_id,
                    MarketRegimeContext.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(MarketRegimeContext.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_market_session(
        self,
        analysis_run_id: UUID,
        signal_id: UUID,
    ) -> MarketSessionContext | None:
        statement: Select[tuple[MarketSessionContext]] = (
            select(MarketSessionContext)
            .where(
                or_(
                    MarketSessionContext.signal_id == signal_id,
                    MarketSessionContext.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(MarketSessionContext.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_multi_timeframe_context(
        self,
        analysis_run_id: UUID,
        signal_id: UUID,
    ) -> MultiTimeframeContext | None:
        statement: Select[tuple[MultiTimeframeContext]] = (
            select(MultiTimeframeContext)
            .where(
                or_(
                    MultiTimeframeContext.signal_id == signal_id,
                    MultiTimeframeContext.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(MultiTimeframeContext.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_cross_asset_context_run(
        self,
        analysis_run_id: UUID,
        signal_id: UUID,
    ) -> CrossAssetContextRun | None:
        statement: Select[tuple[CrossAssetContextRun]] = (
            select(CrossAssetContextRun)
            .where(
                or_(
                    CrossAssetContextRun.signal_id == signal_id,
                    CrossAssetContextRun.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(CrossAssetContextRun.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_cross_asset_results(
        self,
        context_run_id: UUID | None,
        limit: int = 20,
    ) -> list[CrossAssetContextResult]:
        if context_run_id is None:
            return []
        statement: Select[tuple[CrossAssetContextResult]] = (
            select(CrossAssetContextResult)
            .where(CrossAssetContextResult.context_run_id == context_run_id)
            .order_by(CrossAssetContextResult.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_outcomes(self, signal_id: UUID) -> list[SignalOutcome]:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(SignalOutcome.signal_id == signal_id)
            .order_by(SignalOutcome.horizon_minutes.asc(), SignalOutcome.created_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_data_quality_run(
        self,
        analysis_run: AnalysisRun,
    ) -> DataQualityRun | None:
        statement: Select[tuple[DataQualityRun]] = (
            select(DataQualityRun)
            .where(
                DataQualityRun.workspace_id == analysis_run.workspace_id,
                DataQualityRun.symbol_id == analysis_run.symbol_id,
                DataQualityRun.timeframe == analysis_run.timeframe,
            )
            .order_by(DataQualityRun.created_at.desc())
        )
        if analysis_run.source_id is not None:
            statement = statement.where(DataQualityRun.source_id == analysis_run.source_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_decision_readiness(
        self,
        signal_id: UUID,
        analysis_run_id: UUID,
    ) -> DecisionReadinessAssessment | None:
        statement: Select[tuple[DecisionReadinessAssessment]] = (
            select(DecisionReadinessAssessment)
            .where(
                or_(
                    DecisionReadinessAssessment.signal_id == signal_id,
                    DecisionReadinessAssessment.analysis_run_id == analysis_run_id,
                )
            )
            .order_by(DecisionReadinessAssessment.updated_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_recent_final_candles(
        self,
        analysis_run: AnalysisRun,
        limit: int = 120,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == analysis_run.workspace_id,
                Candle.symbol_id == analysis_run.symbol_id,
                Candle.timeframe == analysis_run.timeframe,
                Candle.is_final.is_(True),
                Candle.timestamp <= analysis_run.end_time,
            )
            .order_by(Candle.timestamp.desc())
            .limit(limit)
        )
        if analysis_run.source_id is not None:
            statement = statement.where(Candle.source_id == analysis_run.source_id)
        result = await self.session.execute(statement)
        return list(reversed(result.scalars().all()))


def copy_setup_context_values(source: SetupContext, target: SetupContext) -> None:
    target.workspace_id = source.workspace_id
    target.analysis_run_id = source.analysis_run_id
    target.symbol_id = source.symbol_id
    target.timeframe = source.timeframe
    target.status = source.status
    target.directional_bias = source.directional_bias
    target.setup_quality_label = source.setup_quality_label
    target.setup_quality_score = source.setup_quality_score
    target.invalidation_context_json = source.invalidation_context_json
    target.observation_zones_json = source.observation_zones_json
    target.target_context_zones_json = source.target_context_zones_json
    target.wait_conditions_json = source.wait_conditions_json
    target.avoid_reasons_json = source.avoid_reasons_json
    target.timeframe_agreement_json = source.timeframe_agreement_json
    target.data_quality_warnings_json = source.data_quality_warnings_json
    target.risk_notes_json = source.risk_notes_json
    target.next_observations_json = source.next_observations_json
    target.summary = source.summary
    target.metadata_json = source.metadata_json
