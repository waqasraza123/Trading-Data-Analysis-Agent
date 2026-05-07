from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advanced_features.models import AdvancedFeatureSnapshot
from app.modules.analysis.models import AnalysisRun, AnalysisRunStatus
from app.modules.candles.models import Candle
from app.modules.data_quality.models import DataQualityRun
from app.modules.equity_research.models import (
    EquityCatalystContext,
    EquitySwingCandidate,
    EquitySwingScanRun,
    EquityUniverse,
    EquityUniverseMember,
)
from app.modules.features.models import FeatureSnapshot
from app.modules.indicators.models import IndicatorSnapshot
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_scans.models import MarketWatchlist, MarketWatchlistItem
from app.modules.news.models import NewsEvent
from app.modules.setup_context.models import SetupContext
from app.modules.signals.models import Signal


@dataclass(frozen=True)
class EquityResearchArtifacts:
    analysis_run: AnalysisRun | None = None
    signal: Signal | None = None
    setup_context: SetupContext | None = None
    feature_snapshot: FeatureSnapshot | None = None
    indicator_snapshot: IndicatorSnapshot | None = None
    advanced_feature_snapshot: AdvancedFeatureSnapshot | None = None
    market_memory: RollingMarketStateSnapshot | None = None
    data_quality_run: DataQualityRun | None = None
    catalysts: list[EquityCatalystContext] | None = None
    news_events: list[NewsEvent] | None = None


class EquityResearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_universe(self, universe: EquityUniverse) -> EquityUniverse:
        self.session.add(universe)
        await self.session.flush()
        await self.session.refresh(universe)
        return universe

    async def get_universe(self, universe_id: UUID) -> EquityUniverse | None:
        return await self.session.get(EquityUniverse, universe_id)

    async def list_universes(
        self,
        workspace_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityUniverse]:
        statement: Select[tuple[EquityUniverse]] = (
            select(EquityUniverse)
            .where(EquityUniverse.workspace_id == workspace_id)
            .order_by(EquityUniverse.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(EquityUniverse.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_universe(self, universe: EquityUniverse) -> EquityUniverse:
        await self.session.flush()
        await self.session.refresh(universe)
        return universe

    async def create_member(self, member: EquityUniverseMember) -> EquityUniverseMember:
        self.session.add(member)
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def get_member(self, member_id: UUID) -> EquityUniverseMember | None:
        return await self.session.get(EquityUniverseMember, member_id)

    async def get_member_by_universe_symbol(
        self,
        universe_id: UUID,
        symbol_id: UUID,
    ) -> EquityUniverseMember | None:
        statement = select(EquityUniverseMember).where(
            EquityUniverseMember.universe_id == universe_id,
            EquityUniverseMember.symbol_id == symbol_id,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_members(
        self,
        universe_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> list[EquityUniverseMember]:
        statement: Select[tuple[EquityUniverseMember]] = (
            select(EquityUniverseMember)
            .where(EquityUniverseMember.universe_id == universe_id)
            .order_by(EquityUniverseMember.ticker.asc())
            .limit(limit)
            .offset(offset)
        )
        if is_active is not None:
            statement = statement.where(EquityUniverseMember.is_active.is_(is_active))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_member(self, member: EquityUniverseMember) -> EquityUniverseMember:
        await self.session.flush()
        await self.session.refresh(member)
        return member

    async def get_watchlist(self, watchlist_id: UUID) -> MarketWatchlist | None:
        return await self.session.get(MarketWatchlist, watchlist_id)

    async def list_watchlist_items(
        self,
        watchlist_id: UUID,
        limit: int,
    ) -> list[MarketWatchlistItem]:
        statement = (
            select(MarketWatchlistItem)
            .where(
                MarketWatchlistItem.watchlist_id == watchlist_id,
                MarketWatchlistItem.is_active.is_(True),
            )
            .order_by(MarketWatchlistItem.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create_scan_run(self, run: EquitySwingScanRun) -> EquitySwingScanRun:
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_scan_run(self, scan_run_id: UUID) -> EquitySwingScanRun | None:
        return await self.session.get(EquitySwingScanRun, scan_run_id)

    async def list_scan_runs(
        self,
        workspace_id: UUID,
        status: str | None,
        universe_id: UUID | None,
        watchlist_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[EquitySwingScanRun]:
        statement: Select[tuple[EquitySwingScanRun]] = (
            select(EquitySwingScanRun)
            .where(EquitySwingScanRun.workspace_id == workspace_id)
            .order_by(EquitySwingScanRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(EquitySwingScanRun.status == status)
        if universe_id is not None:
            statement = statement.where(EquitySwingScanRun.universe_id == universe_id)
        if watchlist_id is not None:
            statement = statement.where(EquitySwingScanRun.watchlist_id == watchlist_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_scan_run(self, run: EquitySwingScanRun) -> EquitySwingScanRun:
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def create_candidates(
        self,
        candidates: list[EquitySwingCandidate],
    ) -> list[EquitySwingCandidate]:
        self.session.add_all(candidates)
        await self.session.flush()
        for candidate in candidates:
            await self.session.refresh(candidate)
        return candidates

    async def get_candidate(self, candidate_id: UUID) -> EquitySwingCandidate | None:
        return await self.session.get(EquitySwingCandidate, candidate_id)

    async def list_candidates(
        self,
        scan_run_id: UUID,
        limit: int,
        offset: int,
        candidate_status: str | None = None,
        setup_type: str | None = None,
        setup_quality_label: str | None = None,
    ) -> list[EquitySwingCandidate]:
        statement: Select[tuple[EquitySwingCandidate]] = (
            select(EquitySwingCandidate)
            .where(EquitySwingCandidate.scan_run_id == scan_run_id)
            .order_by(
                EquitySwingCandidate.setup_quality_score.desc(),
                EquitySwingCandidate.updated_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if candidate_status is not None:
            statement = statement.where(EquitySwingCandidate.candidate_status == candidate_status)
        if setup_type is not None:
            statement = statement.where(EquitySwingCandidate.setup_type == setup_type)
        if setup_quality_label is not None:
            statement = statement.where(
                EquitySwingCandidate.setup_quality_label == setup_quality_label
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_final_candles(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        limit: int,
        source_id: UUID | None = None,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.is_final.is_(True),
            )
            .order_by(Candle.timestamp.desc(), Candle.created_at.desc())
            .limit(limit)
        )
        if source_id is not None:
            statement = statement.where(Candle.source_id == source_id)
        result = await self.session.execute(statement)
        return list(reversed(result.scalars().all()))

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
            .limit(1)
        )
        if source_id is not None:
            statement = statement.where(AnalysisRun.source_id == source_id)
        result = await self.session.execute(statement)
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
            .limit(1)
        )
        if analysis_run_id is not None:
            statement = statement.where(Signal.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_setup_context(
        self,
        signal_id: UUID | None,
        analysis_run_id: UUID | None,
    ) -> SetupContext | None:
        if signal_id is None and analysis_run_id is None:
            return None
        statement: Select[tuple[SetupContext]] = select(SetupContext).order_by(
            SetupContext.updated_at.desc()
        )
        if signal_id is not None:
            statement = statement.where(SetupContext.signal_id == signal_id)
        elif analysis_run_id is not None:
            statement = statement.where(SetupContext.analysis_run_id == analysis_run_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_artifacts(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        source_id: UUID | None,
    ) -> EquityResearchArtifacts:
        analysis_run = await self.get_latest_completed_analysis_run(
            workspace_id,
            symbol_id,
            timeframe,
            source_id,
        )
        signal = await self.get_latest_signal(
            workspace_id,
            symbol_id,
            timeframe,
            analysis_run.id if analysis_run is not None else None,
        )
        setup_context = await self.get_latest_setup_context(
            signal.id if signal is not None else None,
            analysis_run.id if analysis_run is not None else None,
        )
        return EquityResearchArtifacts(
            analysis_run=analysis_run,
            signal=signal,
            setup_context=setup_context,
            feature_snapshot=await self.get_feature_snapshot(
                analysis_run.id if analysis_run is not None else None
            ),
            indicator_snapshot=await self.get_indicator_snapshot(
                analysis_run.id if analysis_run is not None else None
            ),
            advanced_feature_snapshot=await self.get_advanced_feature_snapshot(
                analysis_run.id if analysis_run is not None else None
            ),
            market_memory=await self.get_market_memory(workspace_id, symbol_id, timeframe),
            data_quality_run=await self.get_data_quality_run(analysis_run),
            catalysts=await self.list_catalysts(workspace_id, symbol_id, None, 20, 0),
            news_events=await self.list_news_events(workspace_id, symbol_id, None, None, 20),
        )

    async def get_feature_snapshot(self, analysis_run_id: UUID | None) -> FeatureSnapshot | None:
        if analysis_run_id is None:
            return None
        result = await self.session.execute(
            select(FeatureSnapshot)
            .where(FeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(FeatureSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_indicator_snapshot(
        self,
        analysis_run_id: UUID | None,
    ) -> IndicatorSnapshot | None:
        if analysis_run_id is None:
            return None
        result = await self.session.execute(
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.analysis_run_id == analysis_run_id)
            .order_by(IndicatorSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_advanced_feature_snapshot(
        self,
        analysis_run_id: UUID | None,
    ) -> AdvancedFeatureSnapshot | None:
        if analysis_run_id is None:
            return None
        result = await self.session.execute(
            select(AdvancedFeatureSnapshot)
            .where(AdvancedFeatureSnapshot.analysis_run_id == analysis_run_id)
            .order_by(AdvancedFeatureSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_market_memory(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        timeframe: str,
    ) -> RollingMarketStateSnapshot | None:
        result = await self.session.execute(
            select(RollingMarketStateSnapshot)
            .where(
                RollingMarketStateSnapshot.workspace_id == workspace_id,
                RollingMarketStateSnapshot.symbol_id == symbol_id,
                RollingMarketStateSnapshot.timeframe == timeframe,
            )
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_data_quality_run(self, analysis_run: AnalysisRun | None) -> DataQualityRun | None:
        if analysis_run is None:
            return None
        result = await self.session.execute(
            select(DataQualityRun)
            .where(
                DataQualityRun.workspace_id == analysis_run.workspace_id,
                DataQualityRun.symbol_id == analysis_run.symbol_id,
                DataQualityRun.timeframe == analysis_run.timeframe,
            )
            .order_by(DataQualityRun.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_catalyst(self, catalyst: EquityCatalystContext) -> EquityCatalystContext:
        self.session.add(catalyst)
        await self.session.flush()
        await self.session.refresh(catalyst)
        return catalyst

    async def list_catalysts(
        self,
        workspace_id: UUID,
        symbol_id: UUID | None,
        catalyst_type: str | None,
        limit: int,
        offset: int,
    ) -> list[EquityCatalystContext]:
        statement: Select[tuple[EquityCatalystContext]] = (
            select(EquityCatalystContext)
            .where(EquityCatalystContext.workspace_id == workspace_id)
            .order_by(
                EquityCatalystContext.event_time.desc().nullslast(),
                EquityCatalystContext.created_at.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        if symbol_id is not None:
            statement = statement.where(EquityCatalystContext.symbol_id == symbol_id)
        if catalyst_type is not None:
            statement = statement.where(EquityCatalystContext.catalyst_type == catalyst_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_news_events(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        start_time: datetime | None,
        end_time: datetime | None,
        limit: int,
    ) -> list[NewsEvent]:
        statement: Select[tuple[NewsEvent]] = (
            select(NewsEvent)
            .where(
                or_(NewsEvent.workspace_id == workspace_id, NewsEvent.workspace_id.is_(None)),
                NewsEvent.symbol_id == symbol_id,
            )
            .order_by(NewsEvent.event_time.desc())
            .limit(limit)
        )
        if start_time is not None:
            statement = statement.where(NewsEvent.event_time >= start_time)
        if end_time is not None:
            statement = statement.where(NewsEvent.event_time <= end_time)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
