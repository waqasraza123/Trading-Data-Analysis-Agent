from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.modules.action_plans.service import ReasoningActionPlanService
from app.modules.analysis.models import AnalysisRun, AnalysisRunStatus
from app.modules.analysis.service import AnalysisService
from app.modules.candles.quality import CandleQualityReport
from app.modules.candles.service import CandleService
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
    ScheduledScanRunItemStatus,
    ScheduledScanRunStatus,
)
from app.modules.market_scans.repository import MarketScanRepository
from app.modules.market_scans.scanner import (
    SKIP_MISSING_CANDLES,
    MarketScanExecutor,
    ScanTarget,
)
from app.modules.market_scans.schemas import (
    ScheduledScanConfigCreate,
    WatchlistCreate,
    WatchlistItemCreate,
)
from app.modules.market_scans.service import MarketScanService
from app.modules.reasoning.service import ScenarioReasoningService
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.models import Symbol
from app.modules.symbols.repository import SymbolRepository

NOW = datetime(2026, 4, 30, 12, 0, tzinfo=UTC)


def test_create_watchlist_trims_and_rejects_blank_name() -> None:
    payload = WatchlistCreate(workspace_id=uuid4(), name="  Major FX  ")

    assert payload.name == "Major FX"

    with pytest.raises(ValueError, match="name must not be blank"):
        WatchlistCreate(workspace_id=uuid4(), name="   ")


@pytest.mark.asyncio
async def test_add_watchlist_item_validates_active_symbol() -> None:
    service = service_with_fakes()
    repository = cast(FakeMarketScanRepository, service.repository)
    symbol_repository = cast(FakeSymbolRepository, service.symbol_repository)
    repository.watchlist = watchlist_fixture()
    symbol_repository.symbol = symbol_fixture(is_active=False)

    with pytest.raises(AppError) as error:
        await service.add_watchlist_item(
            repository.watchlist.id,
            WatchlistItemCreate(symbol_id=symbol_repository.symbol.id, timeframe="1m"),
        )

    assert error.value.code == "inactive_symbol"


@pytest.mark.asyncio
async def test_duplicate_watchlist_item_rejected() -> None:
    service = service_with_fakes()
    repository = cast(FakeMarketScanRepository, service.repository)
    symbol_repository = cast(FakeSymbolRepository, service.symbol_repository)
    symbol = symbol_fixture()
    repository.watchlist = watchlist_fixture()
    repository.duplicate_item = watchlist_item_fixture(
        watchlist_id=repository.watchlist.id,
        symbol_id=symbol.id,
    )
    symbol_repository.symbol = symbol

    with pytest.raises(AppError) as error:
        await service.add_watchlist_item(
            repository.watchlist.id,
            WatchlistItemCreate(symbol_id=symbol.id, timeframe="1m"),
        )

    assert error.value.code == "market_watchlist_item_conflict"


@pytest.mark.asyncio
async def test_create_scan_config_validates_positive_lookback_interval() -> None:
    with pytest.raises(ValueError):
        ScheduledScanConfigCreate(
            workspace_id=uuid4(),
            name="BTC scan",
            scan_mode=ScheduledScanMode.SINGLE_SYMBOL,
            symbol_id=uuid4(),
            timeframe="1m",
            lookback_minutes=0,
            interval_seconds=60,
        )

    with pytest.raises(ValueError):
        ScheduledScanConfigCreate(
            workspace_id=uuid4(),
            name="BTC scan",
            scan_mode=ScheduledScanMode.SINGLE_SYMBOL,
            symbol_id=uuid4(),
            timeframe="1m",
            lookback_minutes=60,
            interval_seconds=0,
        )


@pytest.mark.asyncio
async def test_due_scan_config_filtering() -> None:
    repository = FakeMarketScanRepository()
    due_config = scan_config_fixture(next_run_at=NOW - timedelta(seconds=1))
    future_config = scan_config_fixture(next_run_at=NOW + timedelta(seconds=1))
    paused_config = scan_config_fixture(
        status=ScheduledScanConfigStatus.PAUSED.value,
        next_run_at=NOW - timedelta(seconds=1),
    )
    repository.scan_configs = [due_config, future_config, paused_config]

    due = await repository.list_due_scan_configs(now=NOW, limit=10)

    assert due == [due_config]


@pytest.mark.asyncio
async def test_paused_watchlist_is_not_scanned() -> None:
    executor = executor_with_fakes()
    repository = cast(FakeMarketScanRepository, executor.repository)
    config = scan_config_fixture(scan_mode=ScheduledScanMode.WATCHLIST.value)
    run = scan_run_fixture(config)
    repository.watchlist = watchlist_fixture(
        watchlist_id=cast(UUID, config.watchlist_id),
        status=MarketWatchlistStatus.PAUSED.value,
    )

    items = await executor.run_watchlist_scan(config, run)

    assert items == []
    assert run.status == ScheduledScanRunStatus.SKIPPED.value
    assert run.result_json == {"skippedReason": "watchlist_paused"}


@pytest.mark.asyncio
async def test_single_symbol_scan_creates_analysis_run_with_expected_window() -> None:
    executor = executor_with_fakes()
    config = scan_config_fixture(lookback_minutes=60)
    run = scan_run_fixture(config)
    target = ScanTarget(
        symbol_id=cast(UUID, config.symbol_id),
        source_id=config.source_id,
        timeframe="1m",
        include_partial_live_candle=False,
    )

    item = await executor.process_target(config, run, target)

    captured_run = cast(FakeAnalysisService, executor.analysis_service).created_run
    assert captured_run is not None
    assert item.status == ScheduledScanRunItemStatus.COMPLETED.value
    assert captured_run.start_time == NOW - timedelta(minutes=60)
    assert captured_run.end_time == NOW
    assert captured_run.analysis_mode == "scheduled_scan"


@pytest.mark.asyncio
async def test_watchlist_scan_skips_inactive_items() -> None:
    executor = executor_with_fakes()
    repository = cast(FakeMarketScanRepository, executor.repository)
    config = scan_config_fixture(scan_mode=ScheduledScanMode.WATCHLIST.value)
    run = scan_run_fixture(config)
    repository.watchlist = watchlist_fixture(watchlist_id=cast(UUID, config.watchlist_id))
    active_item = watchlist_item_fixture(
        watchlist_id=repository.watchlist.id,
        symbol_id=cast(UUID, config.symbol_id),
        is_active=True,
    )
    inactive_item = watchlist_item_fixture(
        watchlist_id=repository.watchlist.id,
        symbol_id=uuid4(),
        is_active=False,
    )
    repository.watchlist_items = [active_item, inactive_item]

    items = await executor.run_watchlist_scan(config, run)

    assert len(items) == 1
    assert items[0].watchlist_item_id == active_item.id


@pytest.mark.asyncio
async def test_scan_run_records_skipped_items() -> None:
    executor = executor_with_fakes()
    cast(FakeCandleService, executor.candle_service).latest_candle = None
    config = scan_config_fixture()
    run = scan_run_fixture(config)
    target = ScanTarget(
        symbol_id=cast(UUID, config.symbol_id),
        source_id=None,
        timeframe="1m",
        include_partial_live_candle=False,
    )

    item = await executor.process_target(config, run, target)
    executor.complete_run(run, [item])

    assert item.status == ScheduledScanRunItemStatus.SKIPPED.value
    assert item.skipped_reason == SKIP_MISSING_CANDLES
    assert run.skipped_count == 1
    assert run.status == ScheduledScanRunStatus.COMPLETED_WITH_WARNINGS.value


@pytest.mark.asyncio
async def test_run_due_respects_limit() -> None:
    executor = DueLimitExecutor()
    executor.fake_repository.scan_configs = [
        scan_config_fixture(next_run_at=datetime(2000, 1, 1, tzinfo=UTC)),
        scan_config_fixture(next_run_at=datetime(2000, 1, 1, tzinfo=UTC)),
    ]

    runs = await executor.run_due_scan_configs(limit=1)

    assert len(runs) == 1


@pytest.mark.asyncio
async def test_next_run_at_updates_after_run() -> None:
    executor = executor_with_fakes()
    config = scan_config_fixture(interval_seconds=60, next_run_at=NOW)

    await executor.advance_config_schedule(config)

    assert config.last_run_at is not None
    assert config.next_run_at == config.last_run_at + timedelta(seconds=60)


@pytest.mark.asyncio
async def test_include_reasoning_false_does_not_call_reasoning_service() -> None:
    executor = executor_with_fakes()
    config = scan_config_fixture(include_reasoning=False, include_action_plan=False)
    run = scan_run_fixture(config)
    target = ScanTarget(
        symbol_id=cast(UUID, config.symbol_id),
        source_id=None,
        timeframe="1m",
        include_partial_live_candle=False,
    )

    await executor.process_target(config, run, target)

    assert cast(FakeReasoningService, executor.reasoning_service).called is False


@pytest.mark.asyncio
async def test_include_action_plan_false_does_not_call_action_plan_service() -> None:
    executor = executor_with_fakes()
    config = scan_config_fixture(include_reasoning=False, include_action_plan=False)
    run = scan_run_fixture(config)
    target = ScanTarget(
        symbol_id=cast(UUID, config.symbol_id),
        source_id=None,
        timeframe="1m",
        include_partial_live_candle=False,
    )

    await executor.process_target(config, run, target)

    assert cast(FakeActionPlanService, executor.action_plan_service).called is False


def test_no_broker_trading_action_path_exists() -> None:
    assert not hasattr(MarketScanExecutor, "execute_action_item")
    assert not hasattr(MarketScanExecutor, "dispatch_due_notifications")
    assert not hasattr(MarketScanExecutor, "place_order")


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeSymbolRepository:
    def __init__(self) -> None:
        self.symbol = symbol_fixture()

    async def get_by_id(self, symbol_id: UUID) -> Symbol | None:
        if self.symbol.id == symbol_id:
            return self.symbol
        return symbol_fixture(symbol_id=symbol_id)


class FakeDataSourceRepository:
    async def get_by_id(self, data_source_id: UUID) -> None:
        return None


class FakeMarketScanRepository:
    def __init__(self) -> None:
        self.watchlist: MarketWatchlist | None = None
        self.duplicate_item: MarketWatchlistItem | None = None
        self.watchlist_items: list[MarketWatchlistItem] = []
        self.scan_configs: list[ScheduledScanConfig] = []
        self.created_items: list[ScheduledScanRunItem] = []

    async def create_watchlist(self, watchlist: MarketWatchlist) -> MarketWatchlist:
        watchlist.id = watchlist.id or uuid4()
        self.watchlist = watchlist
        return watchlist

    async def get_watchlist(self, watchlist_id: UUID) -> MarketWatchlist | None:
        if self.watchlist is not None and self.watchlist.id == watchlist_id:
            return self.watchlist
        return None

    async def get_duplicate_watchlist_item(
        self,
        watchlist_id: UUID,
        symbol_id: UUID,
        source_id: UUID | None,
        timeframe: str,
        exclude_item_id: UUID | None = None,
    ) -> MarketWatchlistItem | None:
        return self.duplicate_item

    async def create_watchlist_item(
        self,
        item: MarketWatchlistItem,
    ) -> MarketWatchlistItem:
        item.id = item.id or uuid4()
        return item

    async def list_watchlist_items(
        self,
        watchlist_id: UUID,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> list[MarketWatchlistItem]:
        items = [item for item in self.watchlist_items if item.watchlist_id == watchlist_id]
        if is_active is not None:
            items = [item for item in items if item.is_active is is_active]
        return items[offset : offset + limit]

    async def list_due_scan_configs(
        self,
        now: datetime,
        limit: int,
        workspace_id: UUID | None = None,
    ) -> list[ScheduledScanConfig]:
        configs = [
            config
            for config in self.scan_configs
            if config.status == ScheduledScanConfigStatus.ACTIVE.value
            and config.next_run_at is not None
            and config.next_run_at <= now
            and (workspace_id is None or config.workspace_id == workspace_id)
        ]
        return configs[:limit]

    async def create_scan_run_item(
        self,
        item: ScheduledScanRunItem,
    ) -> ScheduledScanRunItem:
        item.id = item.id or uuid4()
        self.created_items.append(item)
        return item

    async def update_scan_run_item(
        self,
        item: ScheduledScanRunItem,
    ) -> ScheduledScanRunItem:
        return item

    async def update_scan_run(self, scan_run: ScheduledScanRun) -> ScheduledScanRun:
        return scan_run

    async def update_scan_config(self, config: ScheduledScanConfig) -> ScheduledScanConfig:
        return config


class FakeCandleService:
    def __init__(self) -> None:
        self.latest_candle: SimpleNamespace | None = SimpleNamespace(timestamp=NOW)

    async def get_latest_candle(self, **kwargs: object) -> SimpleNamespace:
        if self.latest_candle is None:
            raise AppError(404, "latest_candle_not_found", "Latest candle not found")
        return self.latest_candle

    async def calculate_window_quality(self, **kwargs: object) -> CandleQualityReport:
        return CandleQualityReport(
            expected_candles=61,
            available_final_candles=61,
            available_partial_candles=0,
            missing_candles=0,
            duplicate_candles=0,
            quality_score="1.0000",
            has_partial_latest_candle=False,
        )


class FakeEngineVersionService:
    def current_snapshot(self) -> dict[str, object]:
        return {"engine": "test"}


class FakeAnalysisService:
    def __init__(self) -> None:
        self.engine_version_service = FakeEngineVersionService()
        self.created_run: AnalysisRun | None = None

    async def build_current_rule_set_snapshot(self) -> dict[str, object]:
        return {"rules": "test"}

    def resolve_window_start(
        self,
        requested_start_time: datetime | None,
        analysis_start_time: datetime,
        timeframe: object,
        candle_count: int,
    ) -> datetime | None:
        return analysis_start_time - timedelta(minutes=candle_count)

    async def create_and_process_run(self, run: AnalysisRun) -> AnalysisRun:
        run.id = run.id or uuid4()
        run.status = AnalysisRunStatus.COMPLETED.value
        self.created_run = run
        return run


class FakeSignalRepository:
    async def get_by_analysis_run_id(self, analysis_run_id: UUID) -> SimpleNamespace:
        return SimpleNamespace(id=uuid4())


class FakeReasoningService:
    def __init__(self) -> None:
        self.called = False

    async def generate_signal_scenarios(self, signal_id: UUID) -> SimpleNamespace:
        self.called = True
        return SimpleNamespace(reasoning_run=SimpleNamespace(id=uuid4(), status="completed"))


class FakeActionPlanService:
    def __init__(self) -> None:
        self.called = False

    async def create_from_reasoning_run(self, reasoning_run_id: UUID) -> SimpleNamespace:
        self.called = True
        return SimpleNamespace(plan=SimpleNamespace(id=uuid4()))


class DueLimitExecutor(MarketScanExecutor):
    def __init__(self) -> None:
        self.fake_repository = FakeMarketScanRepository()
        self.repository = cast(MarketScanRepository, self.fake_repository)

    async def run_scan_config(self, scan_config_id: UUID, force: bool = False) -> ScheduledScanRun:
        config = next(
            config for config in self.fake_repository.scan_configs if config.id == scan_config_id
        )
        return scan_run_fixture(config)


def service_with_fakes() -> MarketScanService:
    repository = FakeMarketScanRepository()
    service = MarketScanService(
        cast(AsyncSession, FakeSession()),
        settings=Settings(_env_file=None),
        repository=cast(MarketScanRepository, repository),
    )
    service.symbol_repository = cast(SymbolRepository, FakeSymbolRepository())
    service.data_source_repository = cast(DataSourceRepository, FakeDataSourceRepository())
    return service


def executor_with_fakes() -> MarketScanExecutor:
    executor = MarketScanExecutor.__new__(MarketScanExecutor)
    executor.session = cast(AsyncSession, FakeSession())
    executor.settings = Settings(_env_file=None)
    executor.repository = cast(MarketScanRepository, FakeMarketScanRepository())
    executor.candle_service = cast(CandleService, FakeCandleService())
    executor.analysis_service = cast(AnalysisService, FakeAnalysisService())
    executor.signal_repository = cast(SignalRepository, FakeSignalRepository())
    executor.reasoning_service = cast(ScenarioReasoningService, FakeReasoningService())
    executor.action_plan_service = cast(ReasoningActionPlanService, FakeActionPlanService())
    executor.symbol_repository = cast(SymbolRepository, FakeSymbolRepository())
    return executor


def symbol_fixture(symbol_id: UUID | None = None, is_active: bool = True) -> Symbol:
    return Symbol(
        id=symbol_id or uuid4(),
        symbol=f"BTCUSD{uuid4().hex[:6]}",
        display_name="BTC/USD",
        market_type="crypto",
        tick_size="0.0100",
        price_precision=2,
        quantity_precision=8,
        is_active=is_active,
    )


def watchlist_fixture(
    watchlist_id: UUID | None = None,
    status: str = MarketWatchlistStatus.ACTIVE.value,
) -> MarketWatchlist:
    return MarketWatchlist(
        id=watchlist_id or uuid4(),
        workspace_id=uuid4(),
        name="Major FX",
        status=status,
        metadata_json={},
    )


def watchlist_item_fixture(
    watchlist_id: UUID,
    symbol_id: UUID,
    is_active: bool = True,
) -> MarketWatchlistItem:
    return MarketWatchlistItem(
        id=uuid4(),
        workspace_id=uuid4(),
        watchlist_id=watchlist_id,
        symbol_id=symbol_id,
        source_id=None,
        timeframe="1m",
        include_partial_live_candle=False,
        is_active=is_active,
        metadata_json={},
    )


def scan_config_fixture(
    scan_mode: str = ScheduledScanMode.SINGLE_SYMBOL.value,
    status: str = ScheduledScanConfigStatus.ACTIVE.value,
    lookback_minutes: int = 60,
    interval_seconds: int = 60,
    next_run_at: datetime | None = NOW,
    include_reasoning: bool = False,
    include_action_plan: bool = False,
) -> ScheduledScanConfig:
    symbol_id = uuid4()
    return ScheduledScanConfig(
        id=uuid4(),
        workspace_id=uuid4(),
        name="BTC scan",
        watchlist_id=uuid4() if scan_mode == ScheduledScanMode.WATCHLIST.value else None,
        symbol_id=symbol_id if scan_mode == ScheduledScanMode.SINGLE_SYMBOL.value else None,
        source_id=None,
        timeframe="1m" if scan_mode == ScheduledScanMode.SINGLE_SYMBOL.value else None,
        scan_mode=scan_mode,
        lookback_minutes=lookback_minutes,
        interval_seconds=interval_seconds,
        include_partial_live_candle=False,
        include_news_correlation=False,
        include_ai_explanation=False,
        include_reasoning=include_reasoning,
        include_action_plan=include_action_plan,
        status=status,
        next_run_at=next_run_at,
        metadata_json={},
    )


def scan_run_fixture(config: ScheduledScanConfig) -> ScheduledScanRun:
    return ScheduledScanRun(
        id=uuid4(),
        workspace_id=config.workspace_id,
        scan_config_id=config.id,
        status=ScheduledScanRunStatus.RUNNING.value,
        scan_mode=config.scan_mode,
        scheduled_for=config.next_run_at,
        started_at=NOW,
        scanned_item_count=0,
        analysis_run_count=0,
        skipped_count=0,
        failed_count=0,
        analysis_run_ids_json=[],
        signal_ids_json=[],
        reasoning_run_ids_json=[],
        action_plan_ids_json=[],
        result_json={},
    )
