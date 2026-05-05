from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppEnvironment, Settings, get_settings
from app.core.errors import AppError
from app.core.time import utc_now
from app.modules.analysis.models import AnalysisRun, AnalysisRunStatus
from app.modules.analysis.schemas import AnalysisRunCreate
from app.modules.analysis.service import AnalysisService
from app.modules.candles.normalizer import RawCandlePayload
from app.modules.candles.timeframes import Timeframe
from app.modules.daily_briefs.models import DailyBriefRun, DailyBriefType
from app.modules.daily_briefs.schemas import DailyBriefCreate, DailyBriefFilters
from app.modules.daily_briefs.service import DailyBriefService
from app.modules.data_sources.models import DataSource, DataSourceStatus, DataSourceType
from app.modules.data_sources.repository import DataSourceRepository
from app.modules.demo_mode.schemas import (
    DemoModeArtifactLink,
    DemoModeFlowStep,
    DemoModeRunFullFlowResponse,
    DemoModeRunRequest,
    DemoModeStatusResponse,
    DemoModeWorkspaceRequest,
    DemoModeWorkspaceResponse,
)
from app.modules.imports.models import ImportBatch
from app.modules.imports.schemas import JsonCandleImportRequest
from app.modules.imports.service import ImportService
from app.modules.market_scans.models import (
    MarketWatchlist,
    ScheduledScanConfig,
    ScheduledScanMode,
    ScheduledScanRun,
)
from app.modules.market_scans.scanner import MarketScanExecutor
from app.modules.market_scans.schemas import (
    ScheduledScanConfigCreate,
    WatchlistCreate,
    WatchlistItemCreate,
)
from app.modules.market_scans.service import MarketScanService
from app.modules.outcomes.models import SignalOutcome
from app.modules.outcomes.service import OutcomeEvaluationService
from app.modules.product_readiness.repository import ProductReadinessRepository
from app.modules.product_readiness.schemas import ProductReadinessRunRead
from app.modules.product_readiness.service import ProductReadinessService
from app.modules.seeding.service import SeedService
from app.modules.setup_context.models import SetupContext
from app.modules.setup_context.service import SetupContextService
from app.modules.signal_priority.models import SignalPriorityScore
from app.modules.signal_priority.service import SignalPriorityService
from app.modules.signals.models import Signal
from app.modules.symbols.models import MarketType, Symbol
from app.modules.symbols.repository import SymbolRepository
from app.modules.synthetic_fixtures.generator import SyntheticFixtureGenerator
from app.modules.synthetic_fixtures.schemas import (
    SyntheticFixtureCandle,
    SyntheticFixtureGenerateRequest,
    SyntheticFixturePattern,
    SyntheticVolumeBehavior,
)
from app.modules.trading_journal.models import JournalDecisionType, JournalEntryStatus
from app.modules.trading_journal.schemas import JournalEntryCreateRequest, JournalEntryRead
from app.modules.trading_journal.service import TradingJournalService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository

DEMO_SOURCE_NAME = "demo_json_import"
DEMO_SOURCE_PROVIDER = "demo_synthetic"
DEMO_ADMIN_EMAIL = "demo-admin@example.test"
DEMO_ADMIN_NAME = "Demo Operator"
DEMO_WATCHLIST_NAME = "Demo Smoke Watchlist"
DEMO_SCAN_CONFIG_NAME = "Demo Smoke Scan"
DEMO_CANDLE_COUNT = 180
DEMO_ANALYSIS_START_INDEX = 60
DEMO_ANALYSIS_FUTURE_CANDLES = 30
DEMO_OUTCOME_HORIZONS = [5, 15]


@dataclass(frozen=True)
class DemoWorkspaceArtifacts:
    workspace: Workspace
    user: User
    source: DataSource
    symbols: list[Symbol]
    timeframes: list[Timeframe]


@dataclass(frozen=True)
class DemoCandleSeries:
    symbol: Symbol
    timeframe: Timeframe
    candles: list[SyntheticFixtureCandle]


class DemoModeService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.workspace_repository = WorkspaceRepository(session)
        self.user_repository = UserRepository(session)
        self.symbol_repository = SymbolRepository(session)
        self.data_source_repository = DataSourceRepository(session)

    async def create_demo_workspace(
        self,
        payload: DemoModeWorkspaceRequest | None = None,
    ) -> DemoModeWorkspaceResponse:
        payload = payload or DemoModeWorkspaceRequest()
        artifacts = await self.prepare_workspace_artifacts(payload)
        return DemoModeWorkspaceResponse(
            enabled=True,
            status="completed",
            message="Demo workspace is ready with demo symbols and synthetic import source.",
            workspace_id=artifacts.workspace.id,
            user_id=artifacts.user.id,
            source_id=artifacts.source.id,
            symbols=[symbol_summary(symbol) for symbol in artifacts.symbols],
            timeframes=[timeframe.value for timeframe in artifacts.timeframes],
            links=workspace_links(artifacts.workspace.id),
        )

    async def run_full_demo_flow(
        self,
        payload: DemoModeRunRequest | None = None,
    ) -> DemoModeRunFullFlowResponse:
        payload = payload or DemoModeRunRequest()
        steps: list[DemoModeFlowStep] = []
        artifacts = await self.prepare_workspace_artifacts(payload)
        steps.append(
            DemoModeFlowStep(
                key="workspace",
                status="completed",
                summary="Demo workspace, user, symbols, and source are ready.",
                metadata={
                    "workspaceId": str(artifacts.workspace.id),
                    "sourceId": str(artifacts.source.id),
                    "symbolCount": len(artifacts.symbols),
                    "timeframes": [timeframe.value for timeframe in artifacts.timeframes],
                },
            )
        )
        candle_series = self.generate_demo_candles(artifacts.symbols, artifacts.timeframes)
        steps.append(
            DemoModeFlowStep(
                key="synthetic_candles",
                status="completed",
                summary="Deterministic synthetic candle fixtures were generated.",
                metadata={
                    "seriesCount": len(candle_series),
                    "candlesPerSeries": DEMO_CANDLE_COUNT,
                    "externalProvidersUsed": False,
                },
            )
        )
        import_batches = await self.import_demo_candles(artifacts, candle_series)
        steps.append(
            DemoModeFlowStep(
                key="imports",
                status="completed",
                summary="Synthetic candles were imported through the existing JSON import path.",
                metadata={"importBatchIds": [str(batch.id) for batch in import_batches]},
            )
        )
        analysis_runs = await self.run_demo_analysis(artifacts, candle_series)
        signals = await self.load_signals(analysis_runs)
        steps.append(
            DemoModeFlowStep(
                key="analysis",
                status="completed",
                summary="Analysis runs completed through the deterministic lifecycle.",
                metadata={
                    "analysisRunIds": [str(run.id) for run in analysis_runs],
                    "signalIds": [str(signal.id) for signal in signals],
                },
            )
        )
        setup_contexts = await self.generate_demo_setup_context(signals, payload.force_recompute)
        priority_scores = await self.score_demo_priorities(signals, payload.force_recompute)
        outcomes = await self.evaluate_demo_outcomes(signals, payload.force_recompute)
        steps.append(
            DemoModeFlowStep(
                key="context_priority_outcomes",
                status="completed",
                summary=(
                    "Setup context, review priority, and observed outcome artifacts were "
                    "generated."
                ),
                metadata={
                    "setupContextIds": [str(item.id) for item in setup_contexts],
                    "priorityScoreIds": [str(item.id) for item in priority_scores],
                    "outcomeIds": [str(item.id) for item in outcomes],
                },
            )
        )
        watchlist, scan_config, scan_run = await self.run_demo_scan(artifacts)
        steps.append(
            DemoModeFlowStep(
                key="scan",
                status="completed" if scan_run is not None else "skipped",
                summary="Demo watchlist scan artifacts were prepared and run.",
                metadata={
                    "watchlistId": str(watchlist.id) if watchlist is not None else None,
                    "scanConfigId": str(scan_config.id) if scan_config is not None else None,
                    "scanRunId": str(scan_run.id) if scan_run is not None else None,
                },
            )
        )
        brief = await self.create_demo_daily_brief(artifacts, watchlist.id if watchlist else None)
        journal_entry = await self.create_demo_journal_entry(
            artifacts,
            signals,
            setup_contexts,
            payload.include_journal_entry,
        )
        readiness_run = await self.create_demo_readiness_run(artifacts.workspace.id)
        steps.append(
            DemoModeFlowStep(
                key="brief_surface",
                status="completed",
                summary="A daily brief, optional journal note, and readiness run were created.",
                metadata={
                    "dailyBriefId": str(brief.id),
                    "journalEntryId": str(journal_entry.id) if journal_entry is not None else None,
                    "readinessRunId": (
                        str(readiness_run.id) if readiness_run is not None else None
                    ),
                },
            )
        )
        return DemoModeRunFullFlowResponse(
            enabled=True,
            status="completed",
            message="Demo smoke flow completed with synthetic data and review-only artifacts.",
            workspace_id=artifacts.workspace.id,
            user_id=artifacts.user.id,
            source_id=artifacts.source.id,
            symbols=[symbol_summary(symbol) for symbol in artifacts.symbols],
            timeframes=[timeframe.value for timeframe in artifacts.timeframes],
            import_batch_ids=[batch.id for batch in import_batches],
            analysis_run_ids=[run.id for run in analysis_runs],
            signal_ids=[signal.id for signal in signals],
            setup_context_ids=[context.id for context in setup_contexts],
            priority_score_ids=[score.id for score in priority_scores],
            outcome_ids=[outcome.id for outcome in outcomes],
            watchlist_id=watchlist.id if watchlist is not None else None,
            scan_config_id=scan_config.id if scan_config is not None else None,
            scan_run_id=scan_run.id if scan_run is not None else None,
            daily_brief_id=brief.id,
            journal_entry_id=journal_entry.id if journal_entry is not None else None,
            readiness_run_id=readiness_run.id if readiness_run is not None else None,
            steps=steps,
            links=flow_links(
                workspace_id=artifacts.workspace.id,
                signal_ids=[signal.id for signal in signals],
                brief_id=brief.id,
                scan_run_id=scan_run.id if scan_run is not None else None,
                journal_entry_id=journal_entry.id if journal_entry is not None else None,
            ),
        )

    async def prepare_workspace_artifacts(
        self,
        payload: DemoModeWorkspaceRequest,
    ) -> DemoWorkspaceArtifacts:
        workspace = await self.resolve_workspace(payload)
        seed_settings = self.settings.model_copy(
            update={
                "seed_default_workspace_name": workspace.name,
                "seed_default_admin_email": DEMO_ADMIN_EMAIL,
                "seed_default_admin_name": DEMO_ADMIN_NAME,
            }
        )
        await SeedService(self.session).seed(seed_settings)
        refreshed_workspace = await self.workspace_repository.get_by_id(workspace.id)
        if refreshed_workspace is None:
            raise AppError(500, "demo_workspace_missing", "Demo workspace could not be loaded")
        user = await self.user_repository.get_by_workspace_email(workspace.id, DEMO_ADMIN_EMAIL)
        if user is None:
            raise AppError(500, "demo_user_missing", "Demo user could not be loaded")
        symbols = await self.seed_demo_symbols(resolve_symbols(payload, self.settings))
        source = await self.seed_demo_sources(refreshed_workspace)
        timeframes = resolve_timeframes(payload, self.settings)
        return DemoWorkspaceArtifacts(
            workspace=refreshed_workspace,
            user=user,
            source=source,
            symbols=symbols,
            timeframes=timeframes,
        )

    async def resolve_workspace(self, payload: DemoModeWorkspaceRequest) -> Workspace:
        if isinstance(payload, DemoModeRunRequest) and payload.workspace_id is not None:
            workspace = await self.workspace_repository.get_by_id(payload.workspace_id)
            if workspace is None:
                raise AppError(404, "workspace_not_found", "Workspace not found")
            return workspace
        workspace_name = (
            payload.workspace_name
            or self.settings.demo_mode_default_workspace_name
            or "Demo Workspace"
        )
        workspace = await self.workspace_repository.get_by_name(workspace_name)
        if workspace is not None:
            return workspace
        workspace = await self.workspace_repository.create(Workspace(name=workspace_name))
        await self.session.commit()
        return workspace

    async def seed_demo_symbols(self, symbol_codes: list[str]) -> list[Symbol]:
        await SeedService(self.session).seed_symbols()
        symbols: list[Symbol] = []
        for symbol_code in symbol_codes:
            symbol = await self.symbol_repository.get_by_symbol(symbol_code)
            if symbol is None:
                symbol = await self.create_supported_demo_symbol(symbol_code)
            symbols.append(symbol)
        return symbols

    async def create_supported_demo_symbol(self, symbol_code: str) -> Symbol:
        if symbol_code.endswith("USDT") and len(symbol_code) > 4:
            base_asset = symbol_code.removesuffix("USDT")
            symbol = Symbol(
                symbol=symbol_code,
                display_name=f"{base_asset}/USDT",
                market_type=MarketType.CRYPTO.value,
                base_asset=base_asset,
                quote_asset="USDT",
                tick_size=Decimal("0.01"),
                price_precision=8,
                quantity_precision=8,
                is_active=True,
            )
        elif len(symbol_code) == 6:
            symbol = Symbol(
                symbol=symbol_code,
                display_name=f"{symbol_code[:3]}/{symbol_code[3:]}",
                market_type=MarketType.FOREX.value,
                base_asset=symbol_code[:3],
                quote_asset=symbol_code[3:],
                pip_size=Decimal("0.0001"),
                price_precision=10,
                quantity_precision=10,
                is_active=True,
            )
        else:
            raise AppError(
                422,
                "unsupported_demo_symbol",
                f"Demo mode does not know how to create symbol {symbol_code}",
            )
        created = await self.symbol_repository.create(symbol)
        await self.session.commit()
        return created

    async def seed_demo_sources(self, workspace: Workspace) -> DataSource:
        source = await self.data_source_repository.get_by_natural_key(
            workspace_id=workspace.id,
            name=DEMO_SOURCE_NAME,
            provider=DEMO_SOURCE_PROVIDER,
            source_type=DataSourceType.JSON_IMPORT.value,
        )
        config_json = {
            "demo": True,
            "label": "Demo synthetic candle import source",
            "externalProvidersRequired": False,
            "brokerExecution": False,
            "financialAdvice": False,
        }
        if source is None:
            source = await self.data_source_repository.create(
                DataSource(
                    workspace_id=workspace.id,
                    name=DEMO_SOURCE_NAME,
                    source_type=DataSourceType.JSON_IMPORT.value,
                    provider=DEMO_SOURCE_PROVIDER,
                    status=DataSourceStatus.ACTIVE.value,
                    config_json=config_json,
                )
            )
        else:
            source.status = DataSourceStatus.ACTIVE.value
            source.config_json = source.config_json | config_json
            await self.session.flush()
            await self.session.refresh(source)
        await self.session.commit()
        return source

    def generate_demo_candles(
        self,
        symbols: list[Symbol],
        timeframes: list[Timeframe],
    ) -> list[DemoCandleSeries]:
        generator = SyntheticFixtureGenerator(self.settings.synthetic_fixtures_default_seed)
        series: list[DemoCandleSeries] = []
        for symbol_index, symbol in enumerate(symbols):
            for timeframe_index, timeframe in enumerate(timeframes):
                request = fixture_request(symbol, timeframe, symbol_index, timeframe_index)
                response = generator.generate(request)
                series.append(
                    DemoCandleSeries(
                        symbol=symbol,
                        timeframe=timeframe,
                        candles=response.candles,
                    )
                )
        return series

    async def import_demo_candles(
        self,
        artifacts: DemoWorkspaceArtifacts,
        candle_series: list[DemoCandleSeries],
    ) -> list[ImportBatch]:
        batches: list[ImportBatch] = []
        service = ImportService(self.session)
        for series in candle_series:
            batch = await service.process_json_import(
                JsonCandleImportRequest(
                    workspace_id=artifacts.workspace.id,
                    user_id=artifacts.user.id,
                    source_id=artifacts.source.id,
                    symbol_id=series.symbol.id,
                    timeframe=series.timeframe,
                    candles=[raw_candle(candle) for candle in series.candles],
                )
            )
            batches.append(batch)
        return batches

    async def run_demo_analysis(
        self,
        artifacts: DemoWorkspaceArtifacts,
        candle_series: list[DemoCandleSeries],
    ) -> list[AnalysisRun]:
        service = AnalysisService(self.session)
        runs = []
        for series in candle_series:
            if len(series.candles) <= DEMO_ANALYSIS_START_INDEX + DEMO_ANALYSIS_FUTURE_CANDLES:
                raise AppError(500, "demo_candle_window_invalid", "Demo candle window is invalid")
            end_index = len(series.candles) - DEMO_ANALYSIS_FUTURE_CANDLES - 1
            run = await service.create_historical_run(
                AnalysisRunCreate(
                    workspace_id=artifacts.workspace.id,
                    user_id=artifacts.user.id,
                    source_id=artifacts.source.id,
                    symbol_id=series.symbol.id,
                    timeframe=series.timeframe,
                    start_time=series.candles[DEMO_ANALYSIS_START_INDEX].timestamp,
                    end_time=series.candles[end_index].timestamp,
                    warmup_start_time=series.candles[0].timestamp,
                    baseline_start_time=series.candles[0].timestamp,
                )
            )
            if run.status != AnalysisRunStatus.COMPLETED:
                raise AppError(
                    500,
                    "demo_analysis_not_completed",
                    "Demo analysis did not complete successfully",
                )
            runs.append(run)
        return runs

    async def load_signals(self, analysis_runs: list[AnalysisRun]) -> list[Signal]:
        signals: list[Signal] = []
        for run in analysis_runs:
            result = await self.session.execute(
                select(Signal).where(Signal.analysis_run_id == run.id)
            )
            signal = result.scalar_one_or_none()
            if signal is None:
                raise AppError(500, "demo_signal_missing", "Demo signal was not generated")
            signals.append(signal)
        return signals

    async def generate_demo_setup_context(
        self,
        signals: list[Signal],
        force_recompute: bool,
    ) -> list[SetupContext]:
        service = SetupContextService(self.session, self.settings)
        return [
            await service.build_for_signal(signal.id, force_recompute=force_recompute)
            for signal in signals
        ]

    async def score_demo_priorities(
        self,
        signals: list[Signal],
        force_recompute: bool,
    ) -> list[SignalPriorityScore]:
        service = SignalPriorityService(self.session, self.settings)
        return [
            await service.score_signal(signal.id, force_recompute=force_recompute)
            for signal in signals
        ]

    async def evaluate_demo_outcomes(
        self,
        signals: list[Signal],
        force_recompute: bool,
    ) -> list[SignalOutcome]:
        service = OutcomeEvaluationService(self.session, self.settings)
        outcomes = []
        for signal in signals:
            outcomes.extend(
                await service.evaluate_signal_outcomes(
                    signal.id,
                    horizons_minutes=DEMO_OUTCOME_HORIZONS,
                    force_recompute=force_recompute,
                )
            )
        return outcomes

    async def run_demo_scan(
        self,
        artifacts: DemoWorkspaceArtifacts,
    ) -> tuple[MarketWatchlist | None, ScheduledScanConfig | None, ScheduledScanRun | None]:
        watchlist = await self.get_or_create_demo_watchlist(artifacts.workspace.id)
        scan_service = MarketScanService(self.session, self.settings)
        for symbol in artifacts.symbols:
            for timeframe in artifacts.timeframes:
                await self.add_demo_watchlist_item(
                    scan_service=scan_service,
                    watchlist=watchlist,
                    symbol=symbol,
                    source_id=artifacts.source.id,
                    timeframe=timeframe,
                )
        scan_config = await self.get_or_create_demo_scan_config(
            workspace_id=artifacts.workspace.id,
            watchlist_id=watchlist.id,
            source_id=artifacts.source.id,
        )
        scan_run = await MarketScanExecutor(self.session, self.settings).run_scan_config(
            scan_config.id,
            force=True,
        )
        return watchlist, scan_config, scan_run

    async def get_or_create_demo_watchlist(self, workspace_id: UUID) -> MarketWatchlist:
        result = await self.session.execute(
            select(MarketWatchlist).where(
                MarketWatchlist.workspace_id == workspace_id,
                MarketWatchlist.name == DEMO_WATCHLIST_NAME,
            )
        )
        watchlist = result.scalar_one_or_none()
        if watchlist is not None:
            return watchlist
        return await MarketScanService(self.session, self.settings).create_watchlist(
            WatchlistCreate(
                workspace_id=workspace_id,
                name=DEMO_WATCHLIST_NAME,
                description="Demo-only deterministic smoke validation watchlist.",
                metadata_json=demo_metadata("watchlist"),
            )
        )

    async def add_demo_watchlist_item(
        self,
        scan_service: MarketScanService,
        watchlist: MarketWatchlist,
        symbol: Symbol,
        source_id: UUID,
        timeframe: Timeframe,
    ) -> None:
        try:
            await scan_service.add_watchlist_item(
                watchlist.id,
                WatchlistItemCreate(
                    symbol_id=symbol.id,
                    source_id=source_id,
                    timeframe=timeframe,
                    include_partial_live_candle=False,
                    metadata_json=demo_metadata("watchlist_item"),
                ),
            )
        except AppError as error:
            if error.code != "market_watchlist_item_conflict":
                raise

    async def get_or_create_demo_scan_config(
        self,
        workspace_id: UUID,
        watchlist_id: UUID,
        source_id: UUID,
    ) -> ScheduledScanConfig:
        result = await self.session.execute(
            select(ScheduledScanConfig).where(
                ScheduledScanConfig.workspace_id == workspace_id,
                ScheduledScanConfig.name == DEMO_SCAN_CONFIG_NAME,
            )
        )
        config = result.scalar_one_or_none()
        if config is not None:
            return config
        return await MarketScanService(self.session, self.settings).create_scan_config(
            ScheduledScanConfigCreate(
                workspace_id=workspace_id,
                name=DEMO_SCAN_CONFIG_NAME,
                description="Demo-only deterministic smoke validation scan.",
                watchlist_id=watchlist_id,
                source_id=source_id,
                scan_mode=ScheduledScanMode.WATCHLIST,
                lookback_minutes=120,
                interval_seconds=3600,
                include_partial_live_candle=False,
                include_news_correlation=False,
                include_ai_explanation=False,
                include_reasoning=False,
                include_action_plan=False,
                next_run_at=utc_now(),
                metadata_json=demo_metadata("scan_config"),
            )
        )

    async def create_demo_daily_brief(
        self,
        artifacts: DemoWorkspaceArtifacts,
        watchlist_id: UUID | None,
    ) -> DailyBriefRun:
        now = utc_now()
        return await DailyBriefService(self.session, self.settings).create_brief(
            DailyBriefCreate(
                workspace_id=artifacts.workspace.id,
                brief_type=DailyBriefType.WATCHLIST if watchlist_id else DailyBriefType.DAILY,
                period_start=datetime.combine(now.date(), time.min, tzinfo=UTC),
                period_end=datetime.combine(now.date(), time.max, tzinfo=UTC),
                timezone=self.settings.daily_brief_default_timezone,
                watchlist_id=watchlist_id,
                filters=DailyBriefFilters(
                    symbol_ids=[symbol.id for symbol in artifacts.symbols],
                    timeframes=artifacts.timeframes,
                ),
            )
        )

    async def create_demo_journal_entry(
        self,
        artifacts: DemoWorkspaceArtifacts,
        signals: list[Signal],
        setup_contexts: list[SetupContext],
        include_journal_entry: bool,
    ) -> JournalEntryRead | None:
        if not include_journal_entry or not signals:
            return None
        first_signal = signals[0]
        first_context = setup_contexts[0] if setup_contexts else None
        return await TradingJournalService(self.session, self.settings).create_journal_entry(
            JournalEntryCreateRequest(
                workspace_id=artifacts.workspace.id,
                user_id=artifacts.user.id,
                signal_id=first_signal.id,
                analysis_run_id=first_signal.analysis_run_id,
                setup_context_id=first_context.id if first_context is not None else None,
                title="Demo smoke flow observation",
                status=JournalEntryStatus.SAVED,
                decision_type=JournalDecisionType.OBSERVED,
                user_notes=(
                    "Demo-only observation generated by the product smoke flow. "
                    "This is not a trading instruction."
                ),
                tags=["demo", "smoke-flow"],
                metadata=demo_metadata("journal_entry"),
            )
        )

    async def create_demo_readiness_run(self, workspace_id: UUID) -> ProductReadinessRunRead | None:
        try:
            return await ProductReadinessService(
                ProductReadinessRepository(self.session),
                self.settings,
            ).run_readiness_check(workspace_id)
        except AppError:
            return None


def demo_mode_availability(settings: Settings) -> tuple[bool, str | None]:
    if settings.demo_mode_enabled:
        return True, None
    if settings.app_env == AppEnvironment.DEVELOPMENT:
        return True, None
    return False, "Set DEMO_MODE_ENABLED=true or use APP_ENV=development to run demo mode."


def demo_mode_status_response(settings: Settings) -> DemoModeStatusResponse:
    enabled, reason = demo_mode_availability(settings)
    return DemoModeStatusResponse(
        enabled=enabled,
        status="enabled" if enabled else "disabled",
        app_env=settings.app_env.value,
        reason=reason,
        default_workspace_name=settings.demo_mode_default_workspace_name,
        default_symbols=parse_csv_setting(settings.demo_mode_default_symbols),
        default_timeframes=parse_csv_setting(settings.demo_mode_default_timeframes),
    )


def disabled_workspace_response(settings: Settings) -> DemoModeWorkspaceResponse:
    _, reason = demo_mode_availability(settings)
    return DemoModeWorkspaceResponse(
        enabled=False,
        status="disabled",
        message=reason or "Demo mode is disabled.",
    )


def disabled_flow_response(settings: Settings) -> DemoModeRunFullFlowResponse:
    _, reason = demo_mode_availability(settings)
    return DemoModeRunFullFlowResponse(
        enabled=False,
        status="disabled",
        message=reason or "Demo mode is disabled.",
    )


def parse_csv_setting(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def resolve_symbols(payload: DemoModeWorkspaceRequest, settings: Settings) -> list[str]:
    symbols = payload.symbols or parse_csv_setting(settings.demo_mode_default_symbols)
    if not symbols:
        raise AppError(422, "demo_symbols_required", "At least one demo symbol is required")
    return symbols


def resolve_timeframes(payload: DemoModeWorkspaceRequest, settings: Settings) -> list[Timeframe]:
    raw_timeframes = payload.timeframes or parse_csv_setting(settings.demo_mode_default_timeframes)
    if not raw_timeframes:
        raise AppError(422, "demo_timeframes_required", "At least one demo timeframe is required")
    try:
        return [Timeframe(item.lower()) for item in raw_timeframes]
    except ValueError as error:
        raise AppError(
            422,
            "unsupported_demo_timeframe",
            "Demo timeframe is unsupported",
        ) from error


def fixture_request(
    symbol: Symbol,
    timeframe: Timeframe,
    symbol_index: int,
    timeframe_index: int,
) -> SyntheticFixtureGenerateRequest:
    pattern = fixture_pattern(symbol_index)
    start_price, volatility = fixture_price(symbol.symbol)
    start_time = datetime(2026, 1, 5, tzinfo=UTC) + timedelta(days=symbol_index)
    if timeframe == Timeframe.FIVE_MINUTES:
        start_time += timedelta(hours=timeframe_index)
        minute = start_time.minute - (start_time.minute % 5)
        start_time = start_time.replace(minute=minute, second=0, microsecond=0)
    return SyntheticFixtureGenerateRequest(
        pattern=pattern,
        symbol=symbol.symbol,
        timeframe=timeframe,
        start_time=start_time,
        candle_count=DEMO_CANDLE_COUNT,
        start_price=start_price,
        volatility=volatility,
        volume_behavior=SyntheticVolumeBehavior.TREND,
        seed=10_000 + symbol_index * 100 + timeframe_index,
    )


def fixture_pattern(symbol_index: int) -> SyntheticFixturePattern:
    patterns = [
        SyntheticFixturePattern.BULLISH_BREAKOUT,
        SyntheticFixturePattern.BEARISH_BREAKDOWN,
        SyntheticFixturePattern.BULLISH_CONTINUATION,
        SyntheticFixturePattern.SIDEWAYS_RANGE,
    ]
    return patterns[symbol_index % len(patterns)]


def fixture_price(symbol_code: str) -> tuple[Decimal, Decimal]:
    if symbol_code == "BTCUSDT":
        return Decimal("65000.00"), Decimal("25.00")
    if symbol_code == "ETHUSDT":
        return Decimal("3200.00"), Decimal("3.50")
    if symbol_code.endswith("JPY"):
        return Decimal("145.500"), Decimal("0.010")
    return Decimal("1.1000"), Decimal("0.0005")


def raw_candle(candle: SyntheticFixtureCandle) -> RawCandlePayload:
    return RawCandlePayload(
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


def demo_metadata(artifact_type: str) -> dict[str, object]:
    return {
        "demo": True,
        "artifactType": artifact_type,
        "demoMode": True,
        "syntheticData": True,
        "externalProvidersRequired": False,
        "brokerExecution": False,
        "autoTrading": False,
        "financialAdvice": False,
    }


def symbol_summary(symbol: Symbol) -> dict[str, object]:
    return {
        "id": str(symbol.id),
        "symbol": symbol.symbol,
        "displayName": symbol.display_name,
        "marketType": symbol.market_type,
        "demo": True,
    }


def workspace_links(workspace_id: UUID) -> list[DemoModeArtifactLink]:
    return [
        DemoModeArtifactLink(
            label="Command center",
            href=f"/command-center?workspaceId={workspace_id}",
            artifact_type="workspace",
            artifact_id=str(workspace_id),
        ),
        DemoModeArtifactLink(
            label="Readiness",
            href=f"/readiness?workspaceId={workspace_id}",
            artifact_type="workspace",
            artifact_id=str(workspace_id),
        ),
    ]


def flow_links(
    workspace_id: UUID,
    signal_ids: list[UUID],
    brief_id: UUID,
    scan_run_id: UUID | None,
    journal_entry_id: UUID | None,
) -> list[DemoModeArtifactLink]:
    links = [
        DemoModeArtifactLink(
            label="Command center",
            href=f"/command-center?workspaceId={workspace_id}",
            artifact_type="workspace",
            artifact_id=str(workspace_id),
        ),
        DemoModeArtifactLink(
            label="Daily brief",
            href=f"/brief?workspaceId={workspace_id}&briefId={brief_id}",
            artifact_type="daily_brief",
            artifact_id=str(brief_id),
        ),
        DemoModeArtifactLink(
            label="Signal triage",
            href=f"/triage?workspaceId={workspace_id}",
            artifact_type="workspace",
            artifact_id=str(workspace_id),
        ),
    ]
    if scan_run_id is not None:
        links.append(
            DemoModeArtifactLink(
                label="Scanner run",
                href=f"/scanner?workspaceId={workspace_id}&runId={scan_run_id}",
                artifact_type="scan_run",
                artifact_id=str(scan_run_id),
            )
        )
    for signal_id in signal_ids[:3]:
        links.append(
            DemoModeArtifactLink(
                label=f"Signal {str(signal_id)[:8]}",
                href=f"/signals/{signal_id}",
                artifact_type="signal",
                artifact_id=str(signal_id),
            )
        )
    if journal_entry_id is not None:
        links.append(
            DemoModeArtifactLink(
                label="Journal entry",
                href=f"/journal/{journal_entry_id}",
                artifact_type="journal_entry",
                artifact_id=str(journal_entry_id),
            )
        )
    return links
