from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.market_scans.models import (
    MarketWatchlist,
    MarketWatchlistItem,
    ScheduledScanConfig,
)
from app.modules.market_scans.repository import MarketScanRepository
from app.modules.scanner_presets.models import (
    ScannerPreset,
    ScannerPresetApplication,
    ScannerPresetApplicationStatus,
)
from app.modules.scanner_presets.repository import ScannerPresetRepository
from app.modules.scanner_presets.schemas import ScannerPresetApplyRequest
from app.modules.scanner_presets.seed import default_scanner_presets
from app.modules.scanner_presets.service import ScannerPresetService
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository


@pytest.mark.asyncio
async def test_seed_default_presets_contains_requested_keys() -> None:
    presets = default_scanner_presets("v1")

    assert {preset.key for preset in presets} == {
        "london_open",
        "new_york_open",
        "crypto_24h",
        "high_volatility",
        "trend_continuation",
        "reversal_risk",
        "range_no_directional",
        "needs_confirmation",
        "stale_data_repair",
        "close_of_day_review",
    }
    assert all(preset.metadata_json["doesNotRunScans"] is True for preset in presets)
    assert all(preset.metadata_json["doesNotCreateSetups"] is True for preset in presets)


@pytest.mark.asyncio
async def test_apply_preset_creates_watchlist_and_scan_config_without_running_scan() -> None:
    workspace_id = uuid4()
    symbol = symbol_fixture()
    preset = default_scanner_presets("v1")[0]
    preset.id = uuid4()
    preset_repository = FakeScannerPresetRepository(workspace_id, preset, [symbol])
    market_repository = FakeMarketScanRepository()
    service = ScannerPresetService(
        cast(AsyncSession, FakeSession()),
        settings=Settings(_env_file=None),
        repository=cast(ScannerPresetRepository, preset_repository),
        market_scan_repository=cast(MarketScanRepository, market_repository),
    )
    service.market_scan_service.symbol_repository = cast(
        SymbolRepository,
        FakeSymbolRepository(symbol),
    )
    service.market_scan_service.data_source_repository = cast(
        DataSourceRepository,
        FakeDataSourceRepository(),
    )

    application = await service.apply_preset(
        workspace_id=workspace_id,
        preset_id=preset.id,
        options=ScannerPresetApplyRequest(
            workspace_id=workspace_id,
            symbol_ids=[symbol.id],
            timeframes=["5m", "15m"],
            create_watchlist=True,
            create_scan_config=True,
        ),
    )

    assert application.status == ScannerPresetApplicationStatus.COMPLETED.value
    assert application.watchlist_id == market_repository.watchlist.id
    assert application.scan_config_id == market_repository.scan_config.id
    assert len(market_repository.items) == 2
    assert market_repository.scan_config.scan_mode == "watchlist"
    assert application.applied_config_json["doesNotRunScans"] is True


class FakeSession:
    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeScannerPresetRepository:
    def __init__(self, workspace_id: UUID, preset: ScannerPreset, symbols: list[Symbol]) -> None:
        self.workspace_id = workspace_id
        self.preset = preset
        self.symbols = symbols
        self.application: ScannerPresetApplication | None = None

    async def get_preset_by_id(self, preset_id: UUID) -> ScannerPreset | None:
        return self.preset if self.preset.id == preset_id else None

    async def get_workspace(self, workspace_id: UUID) -> SimpleNamespace | None:
        if workspace_id == self.workspace_id:
            return SimpleNamespace(id=workspace_id)
        return None

    async def get_preference_profile(self, profile_id: UUID) -> None:
        return None

    async def get_symbols_by_ids(self, symbol_ids: list[UUID]) -> list[Symbol]:
        by_id = {symbol.id: symbol for symbol in self.symbols}
        return [by_id[symbol_id] for symbol_id in symbol_ids if symbol_id in by_id]

    async def create_application(
        self,
        application: ScannerPresetApplication,
    ) -> ScannerPresetApplication:
        application.id = application.id or uuid4()
        self.application = application
        return application


class FakeMarketScanRepository:
    def __init__(self) -> None:
        self.watchlist: MarketWatchlist = cast(MarketWatchlist, None)
        self.items: list[MarketWatchlistItem] = []
        self.scan_config: ScheduledScanConfig = cast(ScheduledScanConfig, None)

    async def create_watchlist(self, watchlist: MarketWatchlist) -> MarketWatchlist:
        watchlist.id = watchlist.id or uuid4()
        self.watchlist = watchlist
        return watchlist

    async def get_watchlist(self, watchlist_id: UUID) -> MarketWatchlist | None:
        if self.watchlist is not None and self.watchlist.id == watchlist_id:
            return self.watchlist
        return None

    async def create_watchlist_item(self, item: MarketWatchlistItem) -> MarketWatchlistItem:
        item.id = item.id or uuid4()
        self.items.append(item)
        return item

    async def create_scan_config(self, config: ScheduledScanConfig) -> ScheduledScanConfig:
        config.id = config.id or uuid4()
        self.scan_config = config
        return config


class FakeSymbolRepository:
    def __init__(self, symbol: Symbol) -> None:
        self.symbol = symbol

    async def get_by_id(self, symbol_id: UUID) -> Symbol | None:
        return self.symbol if self.symbol.id == symbol_id else None


class FakeDataSourceRepository:
    async def get_by_id(self, data_source_id: UUID) -> None:
        return None


def symbol_fixture() -> Symbol:
    return Symbol(
        id=uuid4(),
        symbol="EURUSD",
        display_name="EUR/USD",
        market_type="forex",
        pip_size="0.0001",
        price_precision=5,
        quantity_precision=2,
        is_active=True,
    )
