import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.action_plans.service import ReasoningActionPlanService
from app.modules.analysis.models import AnalysisMode, AnalysisRun, AnalysisRunStatus
from app.modules.analysis.service import (
    ANALYSIS_LIFECYCLE_ENGINE_VERSION,
    ANALYSIS_LIFECYCLE_RULE_SET_VERSION,
    DEFAULT_BASELINE_CANDLES,
    DEFAULT_WARMUP_CANDLES,
    AnalysisService,
)
from app.modules.candles.quality import CandleQualityReport
from app.modules.candles.service import CandleService
from app.modules.candles.timeframes import Timeframe
from app.modules.market_scans.models import (
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
from app.modules.reasoning.models import ReasoningRunStatus
from app.modules.reasoning.service import ScenarioReasoningService
from app.modules.signals.repository import SignalRepository
from app.modules.symbols.repository import SymbolRepository

logger = logging.getLogger(__name__)

SKIP_WATCHLIST_PAUSED = "watchlist_paused"
SKIP_SCAN_CONFIG_PAUSED = "scan_config_paused"
SKIP_NO_ACTIVE_ITEMS = "no_active_watchlist_items"
SKIP_MISSING_CANDLES = "missing_candles"
SKIP_INSUFFICIENT_CANDLES = "insufficient_candles"
SKIP_ANALYSIS_FAILED = "analysis_failed"
SKIP_REASONING_DISABLED = "reasoning_disabled"
SKIP_REASONING_UNAVAILABLE = "reasoning_unavailable"
SKIP_ACTION_PLAN_UNAVAILABLE = "action_plan_unavailable"
SKIP_UNSUPPORTED_SCAN_MODE = "unsupported_scan_mode"


@dataclass(frozen=True)
class ScanTarget:
    symbol_id: UUID
    source_id: UUID | None
    timeframe: str
    include_partial_live_candle: bool
    watchlist_item_id: UUID | None = None


class MarketScanExecutor:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        repository: MarketScanRepository | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repository = repository or MarketScanRepository(session)
        self.candle_service = CandleService(session)
        self.analysis_service = AnalysisService(session)
        self.signal_repository = SignalRepository(session)
        self.reasoning_service = ScenarioReasoningService(session, settings=self.settings)
        self.action_plan_service = ReasoningActionPlanService(session, settings=self.settings)
        self.symbol_repository = SymbolRepository(session)

    async def run_scan_config(self, scan_config_id: UUID, force: bool = False) -> ScheduledScanRun:
        config = await self.get_scan_config(scan_config_id)
        running = await self.repository.get_running_scan_run_for_config(config.id)
        if running is not None:
            return running
        scheduled_for = utc_now() if force else config.next_run_at
        existing = await self.repository.get_scan_run_by_scheduled_for(config.id, scheduled_for)
        if existing is not None and not force:
            return existing
        run = await self.create_scan_run(config, scheduled_for)
        logger.info(
            "scheduled_scan_run_started",
            extra={"scan_config_id": str(config.id), "scan_run_id": str(run.id)},
        )
        try:
            await self.execute_scan_run(config, run)
        except Exception as error:
            run.status = ScheduledScanRunStatus.FAILED.value
            run.error_message = self.safe_error_message(error)
            run.completed_at = utc_now()
            await self.repository.update_scan_run(run)
            await self.advance_config_schedule(config)
            await self.session.commit()
            logger.exception(
                "scheduled_scan_run_failed",
                extra={"scan_config_id": str(config.id), "scan_run_id": str(run.id)},
            )
            return run
        await self.advance_config_schedule(config)
        await self.session.commit()
        return run

    async def run_due_scan_configs(
        self,
        workspace_id: UUID | None = None,
        limit: int = 50,
    ) -> list[ScheduledScanRun]:
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
        runs: list[ScheduledScanRun] = []
        for config in configs:
            runs.append(await self.run_scan_config(config.id))
        return runs

    async def run_single_symbol_scan(
        self,
        config: ScheduledScanConfig,
        run: ScheduledScanRun,
    ) -> list[ScheduledScanRunItem]:
        if config.symbol_id is None or config.timeframe is None:
            await self.mark_run_skipped(run, SKIP_UNSUPPORTED_SCAN_MODE)
            return []
        return [
            await self.process_target(
                config=config,
                run=run,
                target=ScanTarget(
                    symbol_id=config.symbol_id,
                    source_id=config.source_id,
                    timeframe=config.timeframe,
                    include_partial_live_candle=config.include_partial_live_candle,
                ),
            )
        ]

    async def run_watchlist_scan(
        self,
        config: ScheduledScanConfig,
        run: ScheduledScanRun,
    ) -> list[ScheduledScanRunItem]:
        if config.watchlist_id is None:
            await self.mark_run_skipped(run, SKIP_UNSUPPORTED_SCAN_MODE)
            return []
        watchlist = await self.repository.get_watchlist(config.watchlist_id)
        if watchlist is None:
            await self.mark_run_skipped(run, SKIP_UNSUPPORTED_SCAN_MODE)
            return []
        if watchlist.status != MarketWatchlistStatus.ACTIVE.value:
            await self.mark_run_skipped(run, SKIP_WATCHLIST_PAUSED)
            return []
        items = await self.repository.list_watchlist_items(
            watchlist_id=watchlist.id,
            is_active=True,
            limit=500,
            offset=0,
        )
        if not items:
            await self.mark_run_skipped(run, SKIP_NO_ACTIVE_ITEMS)
            return []
        run_items: list[ScheduledScanRunItem] = []
        for item in items:
            target = self.target_from_watchlist_item(item, config)
            run_items.append(await self.process_target(config, run, target))
        return run_items

    async def execute_scan_run(
        self,
        config: ScheduledScanConfig,
        run: ScheduledScanRun,
    ) -> None:
        if config.status != ScheduledScanConfigStatus.ACTIVE.value:
            await self.mark_run_skipped(run, SKIP_SCAN_CONFIG_PAUSED)
            return
        if config.scan_mode == ScheduledScanMode.SINGLE_SYMBOL.value:
            items = await self.run_single_symbol_scan(config, run)
        elif config.scan_mode == ScheduledScanMode.WATCHLIST.value:
            items = await self.run_watchlist_scan(config, run)
        else:
            await self.mark_run_skipped(run, SKIP_UNSUPPORTED_SCAN_MODE)
            return
        if run.status == ScheduledScanRunStatus.SKIPPED.value:
            return
        self.complete_run(run, items)
        await self.repository.update_scan_run(run)
        logger.info(
            "scheduled_scan_run_completed",
            extra={
                "scan_config_id": str(config.id),
                "scan_run_id": str(run.id),
                "status": run.status,
                "analysis_run_count": run.analysis_run_count,
                "skipped_count": run.skipped_count,
                "failed_count": run.failed_count,
            },
        )

    async def process_target(
        self,
        config: ScheduledScanConfig,
        run: ScheduledScanRun,
        target: ScanTarget,
    ) -> ScheduledScanRunItem:
        item = await self.repository.create_scan_run_item(
            ScheduledScanRunItem(
                workspace_id=config.workspace_id,
                scan_run_id=run.id,
                scan_config_id=config.id,
                watchlist_item_id=target.watchlist_item_id,
                symbol_id=target.symbol_id,
                source_id=target.source_id,
                timeframe=target.timeframe,
                status=ScheduledScanRunItemStatus.PENDING.value,
            )
        )
        try:
            await self.ensure_active_symbol(target.symbol_id)
            window = await self.resolve_window(config, target)
            if window is None:
                await self.skip_item(item, SKIP_MISSING_CANDLES)
                return item
            start_time, end_time, quality = window
            if not self.has_enough_candles(quality, target.include_partial_live_candle):
                await self.skip_item(item, SKIP_INSUFFICIENT_CANDLES)
                return item
            analysis_run = await self.create_scheduled_analysis_run(
                config=config,
                target=target,
                start_time=start_time,
                end_time=end_time,
            )
            item.analysis_run_id = analysis_run.id
            if analysis_run.status != AnalysisRunStatus.COMPLETED.value:
                await self.skip_item(item, SKIP_ANALYSIS_FAILED)
                return item
            signal = await self.signal_repository.get_by_analysis_run_id(analysis_run.id)
            if signal is not None:
                item.signal_id = signal.id
            if config.include_reasoning and signal is not None:
                await self.maybe_run_reasoning(config, item, signal.id)
            if config.include_action_plan:
                await self.maybe_create_action_plan(item)
            item.status = ScheduledScanRunItemStatus.COMPLETED.value
            await self.repository.update_scan_run_item(item)
            logger.info(
                "scheduled_scan_item_completed",
                extra={
                    "scan_run_id": str(run.id),
                    "scan_run_item_id": str(item.id),
                    "analysis_run_id": str(item.analysis_run_id),
                    "signal_id": str(item.signal_id) if item.signal_id else None,
                },
            )
            return item
        except Exception as error:
            item.status = ScheduledScanRunItemStatus.FAILED.value
            item.error_message = self.safe_error_message(error)
            await self.repository.update_scan_run_item(item)
            logger.exception(
                "scheduled_scan_item_failed",
                extra={"scan_run_id": str(run.id), "scan_run_item_id": str(item.id)},
            )
            return item

    async def maybe_run_reasoning(
        self,
        config: ScheduledScanConfig,
        item: ScheduledScanRunItem,
        signal_id: UUID,
    ) -> None:
        if not self.settings.llm_reasoning_enabled:
            item.skipped_reason = SKIP_REASONING_DISABLED
            return
        response = await self.reasoning_service.generate_signal_scenarios(signal_id)
        item.reasoning_run_id = response.reasoning_run.id
        if response.reasoning_run.status in {
            ReasoningRunStatus.PROVIDER_NOT_CONFIGURED,
            ReasoningRunStatus.FALLBACK_USED,
            ReasoningRunStatus.BLOCKED,
        }:
            item.skipped_reason = SKIP_REASONING_UNAVAILABLE

    async def maybe_create_action_plan(self, item: ScheduledScanRunItem) -> None:
        if item.reasoning_run_id is None:
            item.skipped_reason = SKIP_ACTION_PLAN_UNAVAILABLE
            return
        response = await self.action_plan_service.create_from_reasoning_run(item.reasoning_run_id)
        item.action_plan_id = response.plan.id

    async def resolve_window(
        self,
        config: ScheduledScanConfig,
        target: ScanTarget,
    ) -> tuple[datetime, datetime, CandleQualityReport] | None:
        timeframe = Timeframe(target.timeframe)
        try:
            latest_candle = await self.candle_service.get_latest_candle(
                workspace_id=config.workspace_id,
                symbol_id=target.symbol_id,
                timeframe=timeframe,
                source_id=target.source_id,
                is_final=None if target.include_partial_live_candle else True,
            )
        except AppError as error:
            if error.code == "latest_candle_not_found":
                return None
            raise
        end_time = latest_candle.timestamp
        start_time = end_time - timedelta(minutes=config.lookback_minutes)
        quality = await self.candle_service.calculate_window_quality(
            workspace_id=config.workspace_id,
            symbol_id=target.symbol_id,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            source_id=target.source_id,
        )
        return start_time, end_time, quality

    async def create_scheduled_analysis_run(
        self,
        config: ScheduledScanConfig,
        target: ScanTarget,
        start_time: datetime,
        end_time: datetime,
    ) -> AnalysisRun:
        timeframe = Timeframe(target.timeframe)
        run = AnalysisRun(
            workspace_id=config.workspace_id,
            user_id=None,
            symbol_id=target.symbol_id,
            source_id=target.source_id,
            timeframe=target.timeframe,
            start_time=start_time,
            end_time=end_time,
            warmup_start_time=self.analysis_service.resolve_window_start(
                None,
                start_time,
                timeframe,
                DEFAULT_WARMUP_CANDLES,
            ),
            baseline_start_time=self.analysis_service.resolve_window_start(
                None,
                start_time,
                timeframe,
                DEFAULT_BASELINE_CANDLES,
            ),
            analysis_mode=AnalysisMode.SCHEDULED_SCAN.value,
            include_partial_live_candle=target.include_partial_live_candle,
            include_news_correlation=config.include_news_correlation,
            include_ai_explanation=config.include_ai_explanation,
            status=AnalysisRunStatus.QUEUED.value,
            engine_version=ANALYSIS_LIFECYCLE_ENGINE_VERSION,
            rule_set_version=ANALYSIS_LIFECYCLE_RULE_SET_VERSION,
            engine_snapshot_json=self.analysis_service.engine_version_service.current_snapshot(),
            rule_set_snapshot_json=await self.analysis_service.build_current_rule_set_snapshot(),
        )
        return await self.analysis_service.create_and_process_run(run)

    async def create_scan_run(
        self,
        config: ScheduledScanConfig,
        scheduled_for: datetime | None,
    ) -> ScheduledScanRun:
        return await self.repository.create_scan_run(
            ScheduledScanRun(
                workspace_id=config.workspace_id,
                scan_config_id=config.id,
                status=ScheduledScanRunStatus.RUNNING.value,
                scan_mode=config.scan_mode,
                scheduled_for=scheduled_for,
                started_at=utc_now(),
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
        )

    async def mark_run_skipped(self, run: ScheduledScanRun, reason: str) -> None:
        run.status = ScheduledScanRunStatus.SKIPPED.value
        run.skipped_count = 1
        run.result_json = {"skippedReason": reason}
        run.completed_at = utc_now()
        await self.repository.update_scan_run(run)
        logger.info(
            "scheduled_scan_run_completed",
            extra={"scan_run_id": str(run.id), "status": run.status, "skipped_reason": reason},
        )

    async def skip_item(self, item: ScheduledScanRunItem, reason: str) -> None:
        item.status = ScheduledScanRunItemStatus.SKIPPED.value
        item.skipped_reason = reason
        await self.repository.update_scan_run_item(item)
        logger.info(
            "scheduled_scan_item_skipped",
            extra={"scan_run_item_id": str(item.id), "skipped_reason": reason},
        )

    async def advance_config_schedule(self, config: ScheduledScanConfig) -> None:
        if config.status != ScheduledScanConfigStatus.ACTIVE.value:
            return
        config.last_run_at = utc_now()
        config.next_run_at = config.last_run_at + timedelta(seconds=config.interval_seconds)
        await self.repository.update_scan_config(config)

    async def get_scan_config(self, scan_config_id: UUID) -> ScheduledScanConfig:
        config = await self.repository.get_scan_config(scan_config_id)
        if config is None:
            raise AppError(404, "scheduled_scan_config_not_found", "Scan config not found")
        return config

    async def ensure_active_symbol(self, symbol_id: UUID) -> None:
        symbol = await self.symbol_repository.get_by_id(symbol_id)
        if symbol is None:
            raise AppError(404, "symbol_not_found", "Symbol not found")
        if not symbol.is_active:
            raise AppError(422, "inactive_symbol", "Inactive symbols cannot be scanned")

    def target_from_watchlist_item(
        self,
        item: MarketWatchlistItem,
        config: ScheduledScanConfig,
    ) -> ScanTarget:
        return ScanTarget(
            symbol_id=item.symbol_id,
            source_id=item.source_id if item.source_id is not None else config.source_id,
            timeframe=item.timeframe,
            include_partial_live_candle=(
                item.include_partial_live_candle or config.include_partial_live_candle
            ),
            watchlist_item_id=item.id,
        )

    def has_enough_candles(
        self,
        quality: CandleQualityReport,
        include_partial_live_candle: bool,
    ) -> bool:
        available_candles = quality.available_final_candles + quality.available_partial_candles
        if quality.expected_candles == 0 or available_candles == 0:
            return False
        if quality.duplicate_candles > 0:
            return False
        if quality.missing_candles == 0:
            return True
        return bool(
            include_partial_live_candle
            and quality.missing_candles == 1
            and quality.has_partial_latest_candle
        )

    def complete_run(
        self,
        run: ScheduledScanRun,
        items: list[ScheduledScanRunItem],
    ) -> None:
        run.scanned_item_count = len(items)
        run.analysis_run_ids_json = [
            str(item.analysis_run_id) for item in items if item.analysis_run_id is not None
        ]
        run.signal_ids_json = [str(item.signal_id) for item in items if item.signal_id is not None]
        run.reasoning_run_ids_json = [
            str(item.reasoning_run_id) for item in items if item.reasoning_run_id is not None
        ]
        run.action_plan_ids_json = [
            str(item.action_plan_id) for item in items if item.action_plan_id is not None
        ]
        run.analysis_run_count = len(run.analysis_run_ids_json)
        run.skipped_count = sum(
            1 for item in items if item.status == ScheduledScanRunItemStatus.SKIPPED.value
        )
        run.failed_count = sum(
            1 for item in items if item.status == ScheduledScanRunItemStatus.FAILED.value
        )
        run.completed_at = utc_now()
        run.result_json = {
            "completedItemCount": sum(
                1 for item in items if item.status == ScheduledScanRunItemStatus.COMPLETED.value
            ),
            "skippedReasons": sorted(
                {
                    item.skipped_reason
                    for item in items
                    if item.skipped_reason is not None
                    and item.status == ScheduledScanRunItemStatus.SKIPPED.value
                }
            ),
        }
        if not items:
            run.status = ScheduledScanRunStatus.SKIPPED.value
        elif run.failed_count and run.failed_count == len(items):
            run.status = ScheduledScanRunStatus.FAILED.value
        elif run.failed_count or run.skipped_count:
            run.status = ScheduledScanRunStatus.COMPLETED_WITH_WARNINGS.value
        else:
            run.status = ScheduledScanRunStatus.COMPLETED.value

    def safe_error_message(self, error: Exception) -> str:
        if isinstance(error, AppError):
            return error.message[:1000]
        return type(error).__name__
