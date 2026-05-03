import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSourceStatus
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    MarketWatchlistStatus,
    ScheduledScanConfig,
    ScheduledScanConfigStatus,
    ScheduledScanMode,
    ScheduledScanRun,
    ScheduledScanRunItem,
)
from app.modules.market_scans.repository import MarketScanRepository
from app.modules.market_scans.schemas import (
    ScheduledScanConfigCreate,
    ScheduledScanConfigUpdate,
    WatchlistCreate,
    WatchlistItemCreate,
    WatchlistItemUpdate,
    WatchlistUpdate,
)
from app.modules.symbols.repository import SymbolRepository

logger = logging.getLogger(__name__)


class MarketScanService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: MarketScanRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or MarketScanRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def create_watchlist(self, payload: WatchlistCreate) -> MarketWatchlist:
        watchlist = MarketWatchlist(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            status=MarketWatchlistStatus.ACTIVE.value,
            metadata_json=payload.metadata_json,
        )
        try:
            created = await self.repository.create_watchlist(watchlist)
            await self.session.commit()
            logger.info(
                "market_watchlist_created",
                extra={"watchlist_id": str(created.id), "workspace_id": str(created.workspace_id)},
            )
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "market_watchlist_conflict",
                "Watchlist could not be created",
            ) from error

    async def list_watchlists(
        self,
        workspace_id: UUID,
        status: MarketWatchlistStatus | None,
        limit: int,
        offset: int,
    ) -> list[MarketWatchlist]:
        return await self.repository.list_watchlists(
            workspace_id=workspace_id,
            status=status.value if status else None,
            limit=limit,
            offset=offset,
        )

    async def get_watchlist(self, watchlist_id: UUID) -> MarketWatchlist:
        watchlist = await self.repository.get_watchlist(watchlist_id)
        if watchlist is None:
            raise AppError(404, "market_watchlist_not_found", "Watchlist not found")
        return watchlist

    async def update_watchlist(
        self,
        watchlist_id: UUID,
        payload: WatchlistUpdate,
    ) -> MarketWatchlist:
        watchlist = await self.get_watchlist(watchlist_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        for field_name, field_value in updates.items():
            if isinstance(field_value, MarketWatchlistStatus):
                field_value = field_value.value
            setattr(watchlist, field_name, field_value)
        try:
            updated = await self.repository.update_watchlist(watchlist)
            await self.session.commit()
            return updated
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "market_watchlist_conflict",
                "Watchlist could not be updated",
            ) from error

    async def add_watchlist_item(
        self,
        watchlist_id: UUID,
        payload: WatchlistItemCreate,
    ) -> MarketWatchlistItem:
        watchlist = await self.get_watchlist(watchlist_id)
        if watchlist.status == MarketWatchlistStatus.ARCHIVED.value:
            raise AppError(422, "watchlist_archived", "Archived watchlists cannot be changed")
        await self.validate_symbol_and_optional_source(
            workspace_id=watchlist.workspace_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
        )
        await self.ensure_watchlist_item_not_duplicate(
            watchlist_id=watchlist.id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=payload.timeframe.value,
        )
        item = MarketWatchlistItem(
            workspace_id=watchlist.workspace_id,
            watchlist_id=watchlist.id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=payload.timeframe.value,
            include_partial_live_candle=payload.include_partial_live_candle,
            is_active=True,
            metadata_json=payload.metadata_json,
        )
        try:
            created = await self.repository.create_watchlist_item(item)
            await self.session.commit()
            logger.info(
                "market_watchlist_item_added",
                extra={
                    "watchlist_id": str(watchlist.id),
                    "watchlist_item_id": str(created.id),
                    "symbol_id": str(created.symbol_id),
                    "timeframe": created.timeframe,
                },
            )
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "market_watchlist_item_conflict",
                "Watchlist item already exists",
            ) from error

    async def list_watchlist_items(
        self,
        watchlist_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> list[MarketWatchlistItem]:
        await self.get_watchlist(watchlist_id)
        return await self.repository.list_watchlist_items(
            watchlist_id=watchlist_id,
            is_active=is_active,
            limit=limit,
            offset=offset,
        )

    async def update_watchlist_item(
        self,
        item_id: UUID,
        payload: WatchlistItemUpdate,
    ) -> MarketWatchlistItem:
        item = await self.get_watchlist_item(item_id)
        watchlist = await self.get_watchlist(item.watchlist_id)
        if watchlist.status == MarketWatchlistStatus.ARCHIVED.value:
            raise AppError(422, "watchlist_archived", "Archived watchlists cannot be changed")
        updates = payload.model_dump(exclude_unset=True, mode="python")
        source_id = updates.get("source_id", item.source_id)
        timeframe = updates.get("timeframe", item.timeframe)
        timeframe_value = timeframe.value if isinstance(timeframe, Timeframe) else str(timeframe)
        await self.validate_symbol_and_optional_source(
            workspace_id=item.workspace_id,
            symbol_id=item.symbol_id,
            source_id=source_id,
        )
        await self.ensure_watchlist_item_not_duplicate(
            watchlist_id=item.watchlist_id,
            symbol_id=item.symbol_id,
            source_id=source_id,
            timeframe=timeframe_value,
            exclude_item_id=item.id,
        )
        for field_name, field_value in updates.items():
            if isinstance(field_value, Timeframe):
                field_value = field_value.value
            setattr(item, field_name, field_value)
        try:
            updated = await self.repository.update_watchlist_item(item)
            await self.session.commit()
            return updated
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "market_watchlist_item_conflict",
                "Watchlist item already exists",
            ) from error

    async def remove_or_deactivate_watchlist_item(self, item_id: UUID) -> MarketWatchlistItem:
        item = await self.get_watchlist_item(item_id)
        item.is_active = False
        updated = await self.repository.update_watchlist_item(item)
        await self.session.commit()
        return updated

    async def get_watchlist_item(self, item_id: UUID) -> MarketWatchlistItem:
        item = await self.repository.get_watchlist_item(item_id)
        if item is None:
            raise AppError(404, "market_watchlist_item_not_found", "Watchlist item not found")
        return item

    async def create_scan_config(
        self,
        payload: ScheduledScanConfigCreate,
    ) -> ScheduledScanConfig:
        lookback_minutes = (
            payload.lookback_minutes or self.settings.market_scan_default_lookback_minutes
        )
        interval_seconds = (
            payload.interval_seconds or self.settings.market_scan_default_interval_seconds
        )
        await self.validate_scan_config_fields(
            workspace_id=payload.workspace_id,
            scan_mode=payload.scan_mode,
            watchlist_id=payload.watchlist_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=payload.timeframe.value if payload.timeframe else None,
        )
        next_run_at = payload.next_run_at or utc_now() + timedelta(seconds=interval_seconds)
        config = ScheduledScanConfig(
            workspace_id=payload.workspace_id,
            name=payload.name,
            description=payload.description,
            watchlist_id=payload.watchlist_id,
            symbol_id=payload.symbol_id,
            source_id=payload.source_id,
            timeframe=payload.timeframe.value if payload.timeframe else None,
            scan_mode=payload.scan_mode.value,
            lookback_minutes=lookback_minutes,
            interval_seconds=interval_seconds,
            include_partial_live_candle=payload.include_partial_live_candle,
            include_news_correlation=payload.include_news_correlation,
            include_ai_explanation=payload.include_ai_explanation,
            include_reasoning=payload.include_reasoning,
            include_action_plan=payload.include_action_plan,
            status=ScheduledScanConfigStatus.ACTIVE.value,
            next_run_at=next_run_at,
            metadata_json=payload.metadata_json,
        )
        try:
            created = await self.repository.create_scan_config(config)
            await self.session.commit()
            logger.info(
                "scheduled_scan_config_created",
                extra={
                    "scan_config_id": str(created.id),
                    "workspace_id": str(created.workspace_id),
                },
            )
            return created
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "scheduled_scan_config_conflict",
                "Scan config could not be created",
            ) from error

    async def list_scan_configs(
        self,
        workspace_id: UUID,
        status: ScheduledScanConfigStatus | None,
        limit: int,
        offset: int,
    ) -> list[ScheduledScanConfig]:
        return await self.repository.list_scan_configs(
            workspace_id=workspace_id,
            status=status.value if status else None,
            limit=limit,
            offset=offset,
        )

    async def get_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig:
        config = await self.repository.get_scan_config(scan_config_id)
        if config is None:
            raise AppError(404, "scheduled_scan_config_not_found", "Scan config not found")
        return config

    async def update_scan_config(
        self,
        scan_config_id: UUID,
        payload: ScheduledScanConfigUpdate,
    ) -> ScheduledScanConfig:
        config = await self.get_scan_config(scan_config_id)
        updates = payload.model_dump(exclude_unset=True, mode="python")
        scan_mode = updates.get("scan_mode", ScheduledScanMode(config.scan_mode))
        watchlist_id = updates.get("watchlist_id", config.watchlist_id)
        symbol_id = updates.get("symbol_id", config.symbol_id)
        source_id = updates.get("source_id", config.source_id)
        timeframe = updates.get("timeframe", config.timeframe)
        timeframe_value = timeframe.value if isinstance(timeframe, Timeframe) else timeframe
        await self.validate_scan_config_fields(
            workspace_id=config.workspace_id,
            scan_mode=scan_mode,
            watchlist_id=watchlist_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe_value,
        )
        for field_name, field_value in updates.items():
            if isinstance(field_value, (ScheduledScanMode, ScheduledScanConfigStatus, Timeframe)):
                field_value = field_value.value
            setattr(config, field_name, field_value)
        try:
            updated = await self.repository.update_scan_config(config)
            await self.session.commit()
            return updated
        except IntegrityError as error:
            await self.session.rollback()
            raise AppError(
                409,
                "scheduled_scan_config_conflict",
                "Scan config could not be updated",
            ) from error

    async def pause_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig:
        config = await self.get_scan_config(scan_config_id)
        config.status = ScheduledScanConfigStatus.PAUSED.value
        updated = await self.repository.update_scan_config(config)
        await self.session.commit()
        return updated

    async def resume_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig:
        config = await self.get_scan_config(scan_config_id)
        config.status = ScheduledScanConfigStatus.ACTIVE.value
        if config.next_run_at is None:
            config.next_run_at = utc_now() + timedelta(seconds=config.interval_seconds)
        updated = await self.repository.update_scan_config(config)
        await self.session.commit()
        return updated

    async def archive_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig:
        config = await self.get_scan_config(scan_config_id)
        config.status = ScheduledScanConfigStatus.ARCHIVED.value
        updated = await self.repository.update_scan_config(config)
        await self.session.commit()
        return updated

    async def list_due_scan_configs(
        self,
        workspace_id: UUID | None = None,
        limit: int = 50,
    ) -> list[ScheduledScanConfig]:
        configs = await self.repository.list_due_scan_configs(
            now=utc_now(),
            workspace_id=workspace_id,
            limit=limit,
        )
        if configs:
            logger.info(
                "scheduled_scan_due_found",
                extra={
                    "due_count": len(configs),
                    "workspace_id": str(workspace_id) if workspace_id else None,
                },
            )
        return configs

    async def get_scan_run(self, scan_run_id: UUID) -> ScheduledScanRun:
        run = await self.repository.get_scan_run(scan_run_id)
        if run is None:
            raise AppError(404, "scheduled_scan_run_not_found", "Scheduled scan run not found")
        return run

    async def list_scan_run_items(
        self,
        scan_run_id: UUID,
        limit: int,
        offset: int,
    ) -> list[ScheduledScanRunItem]:
        await self.get_scan_run(scan_run_id)
        return await self.repository.list_scan_run_items(
            scan_run_id=scan_run_id,
            limit=limit,
            offset=offset,
        )

    async def validate_symbol_and_optional_source(
        self,
        workspace_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
    ) -> None:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Inactive symbols cannot be scanned")
        if source_id is None:
            return
        source = await self.data_source_repository.get_by_id(source_id)
        if source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        if source.status != DataSourceStatus.ACTIVE.value:
            raise AppError(422, "inactive_source", "Inactive sources cannot be scanned")

    async def ensure_watchlist_item_not_duplicate(
        self,
        watchlist_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        timeframe: str,
        exclude_item_id: UUID | None = None,
    ) -> None:
        existing = await self.repository.get_duplicate_watchlist_item(
            watchlist_id=watchlist_id,
            symbol_id=symbol_id,
            source_id=source_id,
            timeframe=timeframe,
            exclude_item_id=exclude_item_id,
        )
        if existing is not None:
            raise AppError(409, "market_watchlist_item_conflict", "Watchlist item already exists")

    async def validate_scan_config_fields(
        self,
        workspace_id: UUID,
        scan_mode: ScheduledScanMode,
        watchlist_id: UUID | None,
        symbol_id: UUID | None,
        source_id: UUID | None,
        timeframe: str | None,
    ) -> None:
        if scan_mode == ScheduledScanMode.WATCHLIST:
            if watchlist_id is None:
                raise AppError(422, "watchlist_required", "watchlist_id is required")
            watchlist = await self.get_watchlist(watchlist_id)
            if watchlist.workspace_id != workspace_id:
                raise AppError(
                    422,
                    "workspace_watchlist_mismatch",
                    "Watchlist does not belong to workspace",
                )
            if watchlist.status == MarketWatchlistStatus.ARCHIVED.value:
                raise AppError(422, "watchlist_archived", "Archived watchlists cannot be scanned")
            await self.validate_optional_source(workspace_id=workspace_id, source_id=source_id)
            return
        if symbol_id is None or timeframe is None:
            raise AppError(422, "single_symbol_required", "symbol_id and timeframe are required")
        await self.validate_symbol_and_optional_source(
            workspace_id=workspace_id,
            symbol_id=symbol_id,
            source_id=source_id,
        )

    async def validate_optional_source(
        self,
        workspace_id: UUID,
        source_id: UUID | None,
    ) -> None:
        if source_id is None:
            return
        source = await self.data_source_repository.get_by_id(source_id)
        if source is None:
            raise AppError(404, "data_source_not_found", "Data source not found")
        if source.workspace_id != workspace_id:
            raise AppError(
                422,
                "workspace_source_mismatch",
                "Data source does not belong to workspace",
            )
        if source.status != DataSourceStatus.ACTIVE.value:
            raise AppError(422, "inactive_source", "Inactive sources cannot be scanned")
