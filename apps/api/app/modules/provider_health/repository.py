from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.candle_gap_recovery.models import CandleGapRecoveryPlan
from app.modules.candles.models import Candle
from app.modules.data_quality.models import DataQualityRun
from app.modules.data_sources.models import DataSource
from app.modules.live.models import LiveFeedSubscription
from app.modules.market_memory.models import RollingMarketStateSnapshot
from app.modules.market_scans.models import MarketWatchlistItem
from app.modules.provider_health.models import ProviderHealthSnapshot
from app.modules.provider_polling.models import (
    ProviderPollingError,
    ProviderPollingRequest,
    ProviderPollingRequestStatus,
)


@dataclass(frozen=True)
class ProviderHealthRefreshCandidate:
    workspace_id: UUID
    source_id: UUID
    symbol_id: UUID | None
    timeframe: str | None


class ProviderHealthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(self, snapshot: ProviderHealthSnapshot) -> ProviderHealthSnapshot:
        self.session.add(snapshot)
        await self.session.flush()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_snapshot(self, snapshot_id: UUID) -> ProviderHealthSnapshot | None:
        return await self.session.get(ProviderHealthSnapshot, snapshot_id)

    async def get_latest_snapshot(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> ProviderHealthSnapshot | None:
        statement: Select[tuple[ProviderHealthSnapshot]] = (
            select(ProviderHealthSnapshot)
            .where(
                ProviderHealthSnapshot.workspace_id == workspace_id,
                ProviderHealthSnapshot.source_id == source_id,
            )
            .order_by(ProviderHealthSnapshot.created_at.desc())
        )
        statement = filter_nullable(statement, ProviderHealthSnapshot.symbol_id, symbol_id)
        statement = filter_nullable(statement, ProviderHealthSnapshot.timeframe, timeframe)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_snapshots(
        self,
        workspace_id: UUID,
        source_id: UUID | None,
        symbol_id: UUID | None,
        timeframe: str | None,
        provider: str | None,
        status: str | None,
        freshness_label: str | None,
        limit: int,
        offset: int,
    ) -> list[ProviderHealthSnapshot]:
        statement: Select[tuple[ProviderHealthSnapshot]] = (
            select(ProviderHealthSnapshot)
            .where(ProviderHealthSnapshot.workspace_id == workspace_id)
            .order_by(ProviderHealthSnapshot.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if source_id is not None:
            statement = statement.where(ProviderHealthSnapshot.source_id == source_id)
        if symbol_id is not None:
            statement = statement.where(ProviderHealthSnapshot.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(ProviderHealthSnapshot.timeframe == timeframe)
        if provider is not None:
            statement = statement.where(ProviderHealthSnapshot.provider == provider)
        if status is not None:
            statement = statement.where(ProviderHealthSnapshot.status == status)
        if freshness_label is not None:
            statement = statement.where(
                ProviderHealthSnapshot.freshness_label == freshness_label
            )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_data_sources(self, workspace_id: UUID, limit: int) -> list[DataSource]:
        statement: Select[tuple[DataSource]] = (
            select(DataSource)
            .where(DataSource.workspace_id == workspace_id)
            .order_by(DataSource.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_refresh_candidates(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[ProviderHealthRefreshCandidate]:
        candidates: list[ProviderHealthRefreshCandidate] = []
        seen: set[tuple[UUID, UUID | None, str | None]] = set()
        for source in await self.list_data_sources(workspace_id, limit):
            key = (source.id, None, None)
            seen.add(key)
            candidates.append(
                ProviderHealthRefreshCandidate(
                    workspace_id=workspace_id,
                    source_id=source.id,
                    symbol_id=None,
                    timeframe=None,
                )
            )
        for candidate in await self.list_candle_candidates(workspace_id, limit):
            key = (candidate.source_id, candidate.symbol_id, candidate.timeframe)
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
        for candidate in await self.list_live_candidates(workspace_id, limit):
            key = (candidate.source_id, candidate.symbol_id, candidate.timeframe)
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
        for candidate in await self.list_watchlist_candidates(workspace_id, limit):
            key = (candidate.source_id, candidate.symbol_id, candidate.timeframe)
            if key not in seen:
                seen.add(key)
                candidates.append(candidate)
        return candidates[:limit]

    async def list_candle_candidates(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[ProviderHealthRefreshCandidate]:
        latest_timestamp = func.max(Candle.timestamp).label("latest_timestamp")
        statement = (
            select(Candle.workspace_id, Candle.source_id, Candle.symbol_id, Candle.timeframe)
            .where(Candle.workspace_id == workspace_id)
            .group_by(Candle.workspace_id, Candle.source_id, Candle.symbol_id, Candle.timeframe)
            .order_by(latest_timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            ProviderHealthRefreshCandidate(
                workspace_id=row.workspace_id,
                source_id=row.source_id,
                symbol_id=row.symbol_id,
                timeframe=row.timeframe,
            )
            for row in result
        ]

    async def list_live_candidates(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[ProviderHealthRefreshCandidate]:
        statement = (
            select(
                LiveFeedSubscription.workspace_id,
                LiveFeedSubscription.source_id,
                LiveFeedSubscription.symbol_id,
                LiveFeedSubscription.timeframe,
            )
            .where(LiveFeedSubscription.workspace_id == workspace_id)
            .order_by(LiveFeedSubscription.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            ProviderHealthRefreshCandidate(
                workspace_id=row.workspace_id,
                source_id=row.source_id,
                symbol_id=row.symbol_id,
                timeframe=row.timeframe,
            )
            for row in result
        ]

    async def list_watchlist_candidates(
        self,
        workspace_id: UUID,
        limit: int,
    ) -> list[ProviderHealthRefreshCandidate]:
        statement = (
            select(
                MarketWatchlistItem.workspace_id,
                MarketWatchlistItem.source_id,
                MarketWatchlistItem.symbol_id,
                MarketWatchlistItem.timeframe,
            )
            .where(
                MarketWatchlistItem.workspace_id == workspace_id,
                MarketWatchlistItem.source_id.is_not(None),
                MarketWatchlistItem.is_active.is_(True),
            )
            .order_by(MarketWatchlistItem.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return [
            ProviderHealthRefreshCandidate(
                workspace_id=row.workspace_id,
                source_id=row.source_id,
                symbol_id=row.symbol_id,
                timeframe=row.timeframe,
            )
            for row in result
            if row.source_id is not None
        ]

    async def get_latest_final_candle(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: str,
    ) -> Candle | None:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.source_id == source_id,
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.is_final.is_(True),
            )
            .order_by(Candle.timestamp.desc(), Candle.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_candles_in_window(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Candle]:
        statement: Select[tuple[Candle]] = (
            select(Candle)
            .where(
                Candle.workspace_id == workspace_id,
                Candle.source_id == source_id,
                Candle.symbol_id == symbol_id,
                Candle.timeframe == timeframe,
                Candle.timestamp >= start_time,
                Candle.timestamp <= end_time,
            )
            .order_by(Candle.timestamp.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_recent_polling_requests(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[ProviderPollingRequest]:
        statement: Select[tuple[ProviderPollingRequest]] = (
            select(ProviderPollingRequest)
            .where(
                ProviderPollingRequest.workspace_id == workspace_id,
                ProviderPollingRequest.source_id == source_id,
            )
            .order_by(ProviderPollingRequest.created_at.desc())
            .limit(limit)
        )
        if symbol_id is not None:
            statement = statement.where(ProviderPollingRequest.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(ProviderPollingRequest.timeframe == timeframe)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_successful_poll(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> ProviderPollingRequest | None:
        statement = self.polling_scope_statement(workspace_id, source_id, symbol_id, timeframe)
        statement = statement.where(
            ProviderPollingRequest.status.in_(
                [
                    ProviderPollingRequestStatus.COMPLETED.value,
                    ProviderPollingRequestStatus.COMPLETED_WITH_WARNINGS.value,
                ]
            )
        ).order_by(
            ProviderPollingRequest.completed_at.desc().nullslast(),
            ProviderPollingRequest.created_at.desc(),
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_latest_failed_poll(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> ProviderPollingRequest | None:
        statement = self.polling_scope_statement(workspace_id, source_id, symbol_id, timeframe)
        statement = statement.where(
            ProviderPollingRequest.status == ProviderPollingRequestStatus.FAILED.value
        ).order_by(
            ProviderPollingRequest.completed_at.desc().nullslast(),
            ProviderPollingRequest.created_at.desc(),
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    def polling_scope_statement(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> Select[tuple[ProviderPollingRequest]]:
        statement: Select[tuple[ProviderPollingRequest]] = select(ProviderPollingRequest).where(
            ProviderPollingRequest.workspace_id == workspace_id,
            ProviderPollingRequest.source_id == source_id,
        )
        if symbol_id is not None:
            statement = statement.where(ProviderPollingRequest.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(ProviderPollingRequest.timeframe == timeframe)
        return statement

    async def list_recent_polling_errors(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
        limit: int,
    ) -> list[ProviderPollingError]:
        request_statement = select(ProviderPollingRequest.id).where(
            ProviderPollingRequest.workspace_id == workspace_id,
            ProviderPollingRequest.source_id == source_id,
        )
        if symbol_id is not None:
            request_statement = request_statement.where(
                ProviderPollingRequest.symbol_id == symbol_id
            )
        if timeframe is not None:
            request_statement = request_statement.where(
                ProviderPollingRequest.timeframe == timeframe
            )
        statement: Select[tuple[ProviderPollingError]] = (
            select(ProviderPollingError)
            .where(
                ProviderPollingError.workspace_id == workspace_id,
                ProviderPollingError.polling_request_id.in_(request_statement),
            )
            .order_by(ProviderPollingError.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_gap_recovery_plan(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: str,
    ) -> CandleGapRecoveryPlan | None:
        statement: Select[tuple[CandleGapRecoveryPlan]] = (
            select(CandleGapRecoveryPlan)
            .where(
                CandleGapRecoveryPlan.workspace_id == workspace_id,
                CandleGapRecoveryPlan.symbol_id == symbol_id,
                CandleGapRecoveryPlan.timeframe == timeframe,
                or_(
                    CandleGapRecoveryPlan.source_id == source_id,
                    CandleGapRecoveryPlan.source_id.is_(None),
                ),
            )
            .order_by(CandleGapRecoveryPlan.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_data_quality_run(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: str,
    ) -> DataQualityRun | None:
        statement: Select[tuple[DataQualityRun]] = (
            select(DataQualityRun)
            .where(
                DataQualityRun.workspace_id == workspace_id,
                DataQualityRun.source_id == source_id,
                DataQualityRun.symbol_id == symbol_id,
                DataQualityRun.timeframe == timeframe,
            )
            .order_by(DataQualityRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_live_subscription(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID | None,
        timeframe: str | None,
    ) -> LiveFeedSubscription | None:
        statement: Select[tuple[LiveFeedSubscription]] = (
            select(LiveFeedSubscription)
            .where(
                LiveFeedSubscription.workspace_id == workspace_id,
                LiveFeedSubscription.source_id == source_id,
            )
            .order_by(LiveFeedSubscription.updated_at.desc())
            .limit(1)
        )
        if symbol_id is not None:
            statement = statement.where(LiveFeedSubscription.symbol_id == symbol_id)
        if timeframe is not None:
            statement = statement.where(LiveFeedSubscription.timeframe == timeframe)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_latest_market_memory(
        self,
        workspace_id: UUID,
        source_id: UUID,
        symbol_id: UUID,
        timeframe: str,
    ) -> RollingMarketStateSnapshot | None:
        statement: Select[tuple[RollingMarketStateSnapshot]] = (
            select(RollingMarketStateSnapshot)
            .where(
                RollingMarketStateSnapshot.workspace_id == workspace_id,
                RollingMarketStateSnapshot.source_id == source_id,
                RollingMarketStateSnapshot.symbol_id == symbol_id,
                RollingMarketStateSnapshot.timeframe == timeframe,
            )
            .order_by(RollingMarketStateSnapshot.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def summarize_workspace(self, workspace_id: UUID) -> dict[str, object]:
        latest_per_identity = (
            select(
                ProviderHealthSnapshot.source_id,
                ProviderHealthSnapshot.symbol_id,
                ProviderHealthSnapshot.timeframe,
                func.max(ProviderHealthSnapshot.created_at).label("latest_created_at"),
            )
            .where(ProviderHealthSnapshot.workspace_id == workspace_id)
            .group_by(
                ProviderHealthSnapshot.source_id,
                ProviderHealthSnapshot.symbol_id,
                ProviderHealthSnapshot.timeframe,
            )
            .subquery()
        )
        statement = select(ProviderHealthSnapshot).join(
            latest_per_identity,
            and_(
                ProviderHealthSnapshot.source_id == latest_per_identity.c.source_id,
                ProviderHealthSnapshot.created_at == latest_per_identity.c.latest_created_at,
                or_(
                    ProviderHealthSnapshot.symbol_id == latest_per_identity.c.symbol_id,
                    and_(
                        ProviderHealthSnapshot.symbol_id.is_(None),
                        latest_per_identity.c.symbol_id.is_(None),
                    ),
                ),
                or_(
                    ProviderHealthSnapshot.timeframe == latest_per_identity.c.timeframe,
                    and_(
                        ProviderHealthSnapshot.timeframe.is_(None),
                        latest_per_identity.c.timeframe.is_(None),
                    ),
                ),
            ),
        )
        result = await self.session.execute(statement)
        snapshots = list(result.scalars().all())
        return {
            "snapshots": snapshots,
            "latestSnapshotAt": max((snapshot.created_at for snapshot in snapshots), default=None),
        }


def filter_nullable(
    statement: Select[tuple[ProviderHealthSnapshot]],
    column: object,
    value: object | None,
) -> Select[tuple[ProviderHealthSnapshot]]:
    if value is None:
        return statement.where(column.is_(None))
    return statement.where(column == value)
