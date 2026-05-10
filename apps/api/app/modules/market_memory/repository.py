from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app.modules.advanced_features.models import AdvancedFeatureSnapshot
from app.modules.analysis.models import AnalysisRun, AnalysisRunStatus
from app.modules.candles.models import Candle
from app.modules.cross_asset_context.models import CrossAssetContextResult, CrossAssetContextRun
from app.modules.data_quality.models import DataQualityRun
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_regimes.models import MarketRegimeContext
from app.modules.market_sessions.models import MarketSessionContext
from app.modules.outcomes.models import SignalOutcome
from app.modules.signals.models import Signal
from app.modules.timeframe_aggregation.models import MultiTimeframeContext


@dataclass(frozen=True)
class MarketMemoryRefreshCandidate:
    workspace_id: UUID
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str


class MarketMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_snapshot(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        state_version: str,
        source_id: UUID | None,
    ) -> RollingMarketStateSnapshot | None:
        statement: Select[tuple[RollingMarketStateSnapshot]] = select(
            RollingMarketStateSnapshot
        ).where(
            RollingMarketStateSnapshot.workspace_id == workspace_id,
            RollingMarketStateSnapshot.symbol_id == symbol_id,
            RollingMarketStateSnapshot.timeframe == timeframe,
            RollingMarketStateSnapshot.state_version == state_version,
        )
        statement = filter_nullable_source(
            statement,
            RollingMarketStateSnapshot.source_id,
            source_id,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_snapshots(
        self,
        workspace_id: UUID,
        limit: int,
        offset: int,
        symbol_id: UUID | None = None,
        source_id: UUID | None = None,
        timeframe: str | None = None,
        freshness_label: str | None = None,
        data_quality_label: str | None = None,
    ) -> list[RollingMarketStateSnapshot]:
        statement: Select[tuple[RollingMarketStateSnapshot]] = (
            select(RollingMarketStateSnapshot)
            .where(RollingMarketStateSnapshot.workspace_id == workspace_id)
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if symbol_id is not None:
            statement = statement.where(RollingMarketStateSnapshot.symbol_id == symbol_id)
        if source_id is not None:
            statement = statement.where(RollingMarketStateSnapshot.source_id == source_id)
        if timeframe is not None:
            statement = statement.where(RollingMarketStateSnapshot.timeframe == timeframe)
        if freshness_label is not None:
            statement = statement.where(
                RollingMarketStateSnapshot.freshness_label == freshness_label
            )
        if data_quality_label is not None:
            statement = statement.where(
                RollingMarketStateSnapshot.data_quality_label == data_quality_label
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def upsert_snapshot(
        self,
        snapshot: RollingMarketStateSnapshot,
        existing: RollingMarketStateSnapshot | None,
    ) -> RollingMarketStateSnapshot:
        if existing is None:
            self.session.add(snapshot)
            await self.session.flush()
            await self.session.refresh(snapshot)
            return snapshot
        copy_snapshot_values(snapshot, existing)
        await self.session.flush()
        await self.session.refresh(existing)
        return existing

    async def get_latest_final_candle(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> Candle | None:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.is_final.is_(True),
            )
            .order_by(Candle.timestamp.desc(), Candle.created_at.desc())
        )
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_completed_analysis_run(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> AnalysisRun | None:
        statement: Select[tuple[AnalysisRun]] = (
            select(AnalysisRun)
            .where(
                AnalysisRun.workspace_id == workspace_id,
                AnalysisRun.symbol_id == symbol_id,
                AnalysisRun.timeframe == timeframe,
                AnalysisRun.status == AnalysisRunStatus.COMPLETED.value,
            )
            .order_by(AnalysisRun.end_time.desc(), AnalysisRun.created_at.desc())
        )
        if source_id is not None:
            statement = statement.where(AnalysisRun.source_id == source_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_signal(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        analysis_run_id: UUID | None,
    ) -> Signal | None:
        statement: Select[tuple[Signal]] = (
            select(Signal)
            .where(
                Signal.workspace_id == workspace_id,
                Signal.symbol_id == symbol_id,
                Signal.timeframe == timeframe,
            )
            .order_by(Signal.created_at.desc())
        )
        if analysis_run_id is not None:
            statement = statement.where(Signal.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_feature_snapshot(self, analysis_run_id: UUID | None) -> FeatureSnapshot | None:
        if analysis_run_id is None:
            return None
        statement: Select[tuple[FeatureSnapshot]] = (
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_indicator_snapshot(
        self,
        analysis_run_id: UUID | None,
    ) -> IndicatorSnapshot | None:
        if analysis_run_id is None:
            return None
        statement: Select[tuple[IndicatorSnapshot]] = (
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.analysis_run_id == analysis_run_id)
            .order_by(IndicatorSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_advanced_feature_snapshot(
        self,
        analysis_run_id: UUID | None,
    ) -> AdvancedFeatureSnapshot | None:
        if analysis_run_id is None:
            return None
        statement: Select[tuple[AdvancedFeatureSnapshot]] = (
            select(AdvancedFeatureSnapshot)
            .where(AdvancedFeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(AdvancedFeatureSnapshot.created_at.desc())
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_market_regime(
        self,
        analysis_run_id: UUID | None,
        signal_id: UUID | None,
    ) -> MarketRegimeContext | None:
        statement: Select[tuple[MarketRegimeContext]] = select(MarketRegimeContext)
        if signal_id is not None:
            statement = statement.where(MarketRegimeContext.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(MarketRegimeContext.analysis_run_id == analysis_run_id)
        else:
            return None
        statement = statement.order_by(MarketRegimeContext.created_at.desc())
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_market_session(
        self,
        analysis_run_id: UUID | None,
        signal_id: UUID | None,
    ) -> MarketSessionContext | None:
        statement: Select[tuple[MarketSessionContext]] = select(MarketSessionContext)
        if signal_id is not None:
            statement = statement.where(MarketSessionContext.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(MarketSessionContext.analysis_run_id == analysis_run_id)
        else:
            return None
        statement = statement.order_by(MarketSessionContext.created_at.desc())
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_multi_timeframe_context(
        self,
        analysis_run_id: UUID | None,
        signal_id: UUID | None,
    ) -> MultiTimeframeContext | None:
        statement: Select[tuple[MultiTimeframeContext]] = select(MultiTimeframeContext)
        if signal_id is not None:
            statement = statement.where(MultiTimeframeContext.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(MultiTimeframeContext.analysis_run_id == analysis_run_id)
        else:
            return None
        statement = statement.order_by(MultiTimeframeContext.created_at.desc())
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_cross_asset_context_run(
        self,
        analysis_run_id: UUID | None,
        signal_id: UUID | None,
    ) -> CrossAssetContextRun | None:
        statement: Select[tuple[CrossAssetContextRun]] = select(CrossAssetContextRun)
        if signal_id is not None:
            statement = statement.where(CrossAssetContextRun.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(CrossAssetContextRun.analysis_run_id == analysis_run_id)
        else:
            return None
        statement = statement.order_by(CrossAssetContextRun.created_at.desc())
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_cross_asset_results(
        self,
        context_run_id: UUID | None,
        limit: int,
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

    async def get_latest_outcome(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        signal_id: UUID | None,
    ) -> SignalOutcome | None:
        statement: Select[tuple[SignalOutcome]] = (
            select(SignalOutcome)
            .where(
                SignalOutcome.workspace_id == workspace_id,
                SignalOutcome.symbol_id == symbol_id,
                SignalOutcome.timeframe == timeframe,
            )
            .order_by(SignalOutcome.created_at.desc())
        )
        if signal_id is not None:
            statement = statement.where(SignalOutcome.signal_id == signal_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_data_quality_run(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> DataQualityRun | None:
        statement: Select[tuple[DataQualityRun]] = (
            select(DataQualityRun)
            .where(
                DataQualityRun.workspace_id == workspace_id,
                DataQualityRun.symbol_id == symbol_id,
                DataQualityRun.timeframe == timeframe,
            )
            .order_by(DataQualityRun.created_at.desc())
        )
        if source_id is not None:
            statement = statement.where(DataQualityRun.source_id == source_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_refresh_candidates(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[MarketMemoryRefreshCandidate]:
        latest_timestamp = func.max(Candle.timestamp).label("latest_timestamp")
        statement = (
            select(Candle.workspace_id, Candle.symbol_id, Candle.source_id, Candle.timeframe)
            .where(Candle.workspace_id == workspace_id, Candle.is_final.is_(True))
            .group_by(Candle.workspace_id, Candle.symbol_id, Candle.source_id, Candle.timeframe)
            .order_by(latest_timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        candidates = [
            MarketMemoryRefreshCandidate(
                workspace_id=row.workspace_id,
                symbol_id=row.symbol_id,
                source_id=row.source_id,
                timeframe=row.timeframe,
            )
            for row in result
        ]
        existing_keys = {
            (candidate.symbol_id, candidate.source_id, candidate.timeframe)
            for candidate in candidates
        }
        for candidate in list(candidates):
            if len(candidates) >= limit:
                break
            aggregate_key = (candidate.symbol_id, None, candidate.timeframe)
            if aggregate_key in existing_keys:
                continue
            existing_keys.add(aggregate_key)
            candidates.append(
                MarketMemoryRefreshCandidate(
                    workspace_id=candidate.workspace_id,
                    symbol_id=candidate.symbol_id,
                    source_id=None,
                    timeframe=candidate.timeframe,
                )
            )
        return candidates


def filter_nullable_source(
    statement: Select[tuple[RollingMarketStateSnapshot]],
    column: InstrumentedAttribute[UUID | None],
    source_id: UUID | None,
) -> Select[tuple[RollingMarketStateSnapshot]]:
    if source_id is None:
        return statement.where(column.is_(None))
    return statement.where(column == source_id)


def copy_snapshot_values(
    source: RollingMarketStateSnapshot,
    target: RollingMarketStateSnapshot,
) -> None:
    target.latest_final_candle_time = source.latest_final_candle_time
    target.latest_analysis_run_id = source.latest_analysis_run_id
    target.latest_signal_id = source.latest_signal_id
    target.latest_outcome_id = source.latest_outcome_id
    target.data_quality_label = source.data_quality_label
    target.freshness_label = source.freshness_label
    target.trend_state = source.trend_state
    target.volatility_state = source.volatility_state
    target.range_state = source.range_state
    target.market_regime_label = source.market_regime_label
    target.market_session_label = source.market_session_label
    target.multi_timeframe_label = source.multi_timeframe_label
    target.cross_asset_label = source.cross_asset_label
    target.latest_signal_bias = source.latest_signal_bias
    target.latest_signal_pattern_type = source.latest_signal_pattern_type
    target.latest_signal_confidence_label = source.latest_signal_confidence_label
    target.context_json = source.context_json
    target.warnings_json = source.warnings_json
