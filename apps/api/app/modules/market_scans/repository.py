from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    ScheduledScanConfig,
    ScheduledScanConfigStatus,
    ScheduledScanRun,
    ScheduledScanRunItem,
    ScheduledScanRunStatus,
)


class MarketScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_watchlist(self, watchlist: MarketWatchlist) -> MarketWatchlist:
        self.session.add(watchlist)
        await self.session.flush()
        await self.session.refresh(watchlist)
        return watchlist

    async def list_watchlists(
        self,
        workspace_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[MarketWatchlist]:
        statement: Select[tuple[MarketWatchlist]] = (
            select(MarketWatchlist)
            .where(MarketWatchlist.workspace_id == workspace_id)
            .order_by(MarketWatchlist.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(MarketWatchlist.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_watchlist(self, watchlist_id: UUID) -> MarketWatchlist | None:
        return await self.session.get(MarketWatchlist, watchlist_id)

    async def update_watchlist(self, watchlist: MarketWatchlist) -> MarketWatchlist:
        await self.session.flush()
        await self.session.refresh(watchlist)
        return watchlist

    async def create_watchlist_item(
        self,
        item: MarketWatchlistItem,
    ) -> MarketWatchlistItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def get_watchlist_item(self, item_id: UUID) -> MarketWatchlistItem | None:
        return await self.session.get(MarketWatchlistItem, item_id)

    async def get_duplicate_watchlist_item(
        self,
        watchlist_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        timeframe: str,
        exclude_item_id: UUID | None = None,
    ) -> MarketWatchlistItem | None:
        statement: Select[tuple[MarketWatchlistItem]] = select(MarketWatchlistItem).where(
            MarketWatchlistItem.watchlist_id == watchlist_id,
            MarketWatchlistItem.symbol_id == symbol_id,
            MarketWatchlistItem.timeframe == timeframe,
        )
        if source_id is None:
            statement = statement.where(MarketWatchlistItem.source_id.is_(None))
        else:
            statement = statement.where(MarketWatchlistItem.source_id == source_id)
        if exclude_item_id is not None:
            statement = statement.where(MarketWatchlistItem.id != exclude_item_id)
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def list_watchlist_items(
        self,
        watchlist_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> list[MarketWatchlistItem]:
        statement: Select[tuple[MarketWatchlistItem]] = (
            select(MarketWatchlistItem)
            .where(MarketWatchlistItem.watchlist_id == watchlist_id)
            .order_by(MarketWatchlistItem.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        if is_active is not None:
            statement = statement.where(MarketWatchlistItem.is_active.is_(is_active))
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_watchlist_item(
        self,
        item: MarketWatchlistItem,
    ) -> MarketWatchlistItem:
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def create_scan_config(self, config: ScheduledScanConfig) -> ScheduledScanConfig:
        self.session.add(config)
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def get_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig | None:
        return await self.session.get(ScheduledScanConfig, scan_config_id)

    async def list_scan_configs(
        self,
        workspace_id: UUID,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[ScheduledScanConfig]:
        statement: Select[tuple[ScheduledScanConfig]] = (
            select(ScheduledScanConfig)
            .where(ScheduledScanConfig.workspace_id == workspace_id)
            .order_by(ScheduledScanConfig.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            statement = statement.where(ScheduledScanConfig.status == status)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def update_scan_config(self, config: ScheduledScanConfig) -> ScheduledScanConfig:
        await self.session.flush()
        await self.session.refresh(config)
        return config

    async def list_due_scan_configs(
        self,
        now: datetime,
        limit: int,
        workspace_id: UUID | None = None,
    ) -> list[ScheduledScanConfig]:
        statement: Select[tuple[ScheduledScanConfig]] = (
            select(ScheduledScanConfig)
            .where(
                ScheduledScanConfig.status == ScheduledScanConfigStatus.ACTIVE.value,
                ScheduledScanConfig.next_run_at.is_not(None),
                ScheduledScanConfig.next_run_at <= now,
            )
            .order_by(ScheduledScanConfig.next_run_at.asc(), ScheduledScanConfig.created_at.asc())
            .limit(limit)
        )
        if workspace_id is not None:
            statement = statement.where(ScheduledScanConfig.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_running_scan_run_for_config(
        self,
        scan_config_id: UUID,
    ) -> ScheduledScanRun | None:
        statement: Select[tuple[ScheduledScanRun]] = select(ScheduledScanRun).where(
            ScheduledScanRun.scan_config_id == scan_config_id,
            ScheduledScanRun.status.in_(
                [ScheduledScanRunStatus.PENDING.value, ScheduledScanRunStatus.RUNNING.value]
            ),
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def get_scan_run_by_scheduled_for(
        self,
        scan_config_id: UUID,
        scheduled_for: datetime | None,
    ) -> ScheduledScanRun | None:
        if scheduled_for is None:
            return None
        statement: Select[tuple[ScheduledScanRun]] = select(ScheduledScanRun).where(
            ScheduledScanRun.scan_config_id == scan_config_id,
            ScheduledScanRun.scheduled_for == scheduled_for,
        )
        result = await self.session.execute(statement.limit(1))
        return result.scalar_one_or_none()

    async def create_scan_run(self, scan_run: ScheduledScanRun) -> ScheduledScanRun:
        self.session.add(scan_run)
        await self.session.flush()
        await self.session.refresh(scan_run)
        return scan_run

    async def update_scan_run(self, scan_run: ScheduledScanRun) -> ScheduledScanRun:
        await self.session.flush()
        await self.session.refresh(scan_run)
        return scan_run

    async def get_scan_run(self, scan_run_id: UUID) -> ScheduledScanRun | None:
        return await self.session.get(ScheduledScanRun, scan_run_id)

    async def create_scan_run_item(
        self,
        item: ScheduledScanRunItem,
    ) -> ScheduledScanRunItem:
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def update_scan_run_item(
        self,
        item: ScheduledScanRunItem,
    ) -> ScheduledScanRunItem:
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def list_scan_run_items(
        self,
        scan_run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[ScheduledScanRunItem]:
        statement: Select[tuple[ScheduledScanRunItem]] = (
            select(ScheduledScanRunItem)
            .where(ScheduledScanRunItem.scan_run_id == scan_run_id)
            .order_by(ScheduledScanRunItem.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_runs(
        self,
        workspace_id: UUID,
        scan_config_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[ScheduledScanRun]:
        statement: Select[tuple[ScheduledScanRun]] = (
            select(ScheduledScanRun)
            .where(ScheduledScanRun.workspace_id == workspace_id)
            .order_by(ScheduledScanRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if scan_config_id is not None:
            statement = statement.where(ScheduledScanRun.scan_config_id == scan_config_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
