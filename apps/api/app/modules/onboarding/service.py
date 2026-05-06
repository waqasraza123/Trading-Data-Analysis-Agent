from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.modules.candles.timeframes import Timeframe
from app.modules.data_sources.models import DataSource
from app.modules.demo_mode.schemas import DemoModeRunRequest
from app.modules.demo_mode.service import DemoModeService, demo_mode_availability
from app.modules.market_scans.models import ScheduledScanMode
from app.modules.market_scans.schemas import (
    ScheduledScanConfigCreate,
    WatchlistCreate,
    WatchlistItemCreate,
)
from app.modules.market_scans.service import MarketScanService
from app.modules.onboarding.schemas import (
    OnboardingActionRequest,
    OnboardingActionResponse,
    OnboardingActionType,
    OnboardingCountStatus,
    OnboardingDailyWorkflowStatus,
    OnboardingDataFreshnessLabel,
    OnboardingDataFreshnessStatus,
    OnboardingDataSourcesStatus,
    OnboardingDemoModeStatus,
    OnboardingNextStep,
    OnboardingNextStepKey,
    OnboardingReadinessLabel,
    OnboardingStatusResponse,
    OnboardingStatusSummary,
    OnboardingStep,
    OnboardingStepState,
    OnboardingUserStatus,
    OnboardingWorkspaceStatus,
)
from app.modules.product_readiness.checks import readiness_check_payload
from app.modules.product_readiness.models import ProductReadinessCheckStatus
from app.modules.product_readiness.repository import ProductReadinessRepository
from app.modules.product_readiness.service import (
    ProductReadinessService,
    calculate_readiness_score,
    choose_readiness_label,
    summarize_readiness,
)
from app.modules.seeding.service import SeedService
from app.modules.symbols.models import Symbol
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.schemas import WorkspaceCreate
from app.modules.workspaces.service import WorkspaceService


class OnboardingService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.readiness_repository = ProductReadinessRepository(session)

    async def get_status(
        self,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> OnboardingStatusResponse:
        workspace = await self.readiness_repository.get_workspace(workspace_id)
        selected_workspace_id = workspace.id if workspace is not None else None
        user = await self.get_user(user_id, selected_workspace_id)
        checks = await ProductReadinessService(
            self.readiness_repository,
            settings=self.settings,
        ).build_checks(workspace_id, selected_workspace_id)
        check_payloads = {check.key: readiness_check_payload(check) for check in checks}
        blockers = [
            payload
            for check in checks
            if check.status == ProductReadinessCheckStatus.FAILED
            for payload in [readiness_check_payload(check)]
        ]
        readiness_warnings = [
            payload
            for check in checks
            if check.status == ProductReadinessCheckStatus.WARNING
            for payload in [readiness_check_payload(check)]
        ]
        readiness_label = choose_readiness_label(checks)
        summary = summarize_readiness(readiness_label, blockers, readiness_warnings)
        symbols = count_status(check_payloads.get("symbols_present"), "active_symbol_count")
        data_sources = data_source_status(check_payloads)
        data_freshness = data_freshness_status(check_payloads.get("fresh_candles_available"))
        watchlists = count_status(check_payloads.get("watchlist_configured"), "active_watchlists")
        scan_configs = count_status(
            check_payloads.get("scan_configured"), "active_scan_config_count"
        )
        daily_workflow = daily_workflow_status(check_payloads.get("daily_workflow_available"))
        demo_available, _ = demo_mode_availability(self.settings)
        response_steps = build_steps(
            workspace=workspace is not None,
            user=user is not None,
            symbols=symbols.configured,
            data_sources=data_sources.configured,
            data_freshness=data_freshness.label,
            watchlists=watchlists.configured,
            scan_configs=scan_configs.configured,
            readiness_label=str(readiness_label.value),
            demo_available=demo_available,
        )
        next_step = choose_next_step(
            workspace=workspace is not None,
            user=user is not None,
            symbols=symbols.configured,
            data_sources=data_sources.configured,
            data_freshness=data_freshness.label,
            watchlists=watchlists.configured,
            scan_configs=scan_configs.configured,
            readiness_label=str(readiness_label.value),
        )
        warnings = [
            str(item.get("summary", "")) for item in readiness_warnings if item.get("summary")
        ]
        missing_sections = [
            step.key
            for step in response_steps
            if step.state in {OnboardingStepState.INCOMPLETE, OnboardingStepState.BLOCKED}
        ]
        return OnboardingStatusResponse(
            status=OnboardingStatusSummary(
                readiness_label=OnboardingReadinessLabel(readiness_label.value),
                readiness_score=calculate_readiness_score(checks),
                summary=summary,
            ),
            workspace=OnboardingWorkspaceStatus(
                exists=workspace is not None,
                workspace_id=workspace.id if workspace is not None else None,
                name=workspace.name if workspace is not None else None,
            ),
            user=OnboardingUserStatus(
                exists=user is not None,
                user_id=user.id if user is not None else None,
                role=user.role if user is not None else None,
            ),
            symbols=symbols,
            data_sources=data_sources,
            data_freshness=data_freshness,
            watchlists=watchlists,
            scan_configs=scan_configs,
            daily_workflow=daily_workflow,
            demo_mode=OnboardingDemoModeStatus(
                available=demo_available,
                enabled=self.settings.demo_mode_enabled,
            ),
            next_step=next_step,
            steps=response_steps,
            warnings=warnings,
            missing_sections=missing_sections,
        )

    async def run_action(self, payload: OnboardingActionRequest) -> OnboardingActionResponse:
        if payload.action_type == OnboardingActionType.CREATE_WORKSPACE:
            workspace = await WorkspaceService(self.session).create_workspace(
                WorkspaceCreate(
                    name=str(payload.options.get("name") or "Market Intelligence Workspace")
                )
            )
            return await self.response_with_status(
                payload,
                "completed",
                "Workspace created.",
                workspace_id=workspace.id,
            )
        if payload.action_type == OnboardingActionType.CREATE_USER:
            workspace_id = await self.require_workspace_id(payload.workspace_id)
            user = await UserService(self.session).create_user(
                UserCreate(
                    workspace_id=workspace_id,
                    email=str(payload.options.get("email") or "operator@example.test"),
                    name=str(payload.options.get("name") or "Operator"),
                    role=UserRole(str(payload.options.get("role") or UserRole.ANALYST.value)),
                )
            )
            return await self.response_with_status(
                payload,
                "completed",
                "Operator context created.",
                workspace_id=workspace_id,
                user_id=user.id,
            )
        if payload.action_type == OnboardingActionType.SEED_SYMBOLS:
            symbols = await SeedService(self.session).seed_symbols()
            await self.session.commit()
            return await self.response_with_status(
                payload,
                "completed",
                "Default symbols seeded.",
                artifact_ids={"symbolIds": [symbol.id for symbol in symbols]},
            )
        if payload.action_type == OnboardingActionType.SEED_DEFAULT_DATA_SOURCES:
            workspace = await self.require_workspace(payload.workspace_id)
            sources = await SeedService(self.session).seed_data_sources(workspace)
            await self.session.commit()
            return await self.response_with_status(
                payload,
                "completed",
                "Default data sources seeded.",
                workspace_id=workspace.id,
                artifact_ids={"dataSourceIds": [source.id for source in sources]},
            )
        if payload.action_type == OnboardingActionType.CREATE_BASIC_WATCHLIST:
            return await self.create_basic_watchlist(payload)
        if payload.action_type == OnboardingActionType.CREATE_BASIC_SCAN_CONFIG:
            return await self.create_basic_scan_config(payload)
        if payload.action_type == OnboardingActionType.RUN_READINESS_CHECK:
            workspace_id = payload.workspace_id
            run = await ProductReadinessService(
                self.readiness_repository,
                settings=self.settings,
            ).run_readiness_check(workspace_id)
            return await self.response_with_status(
                payload,
                "completed",
                "Readiness check completed.",
                workspace_id=run.workspace_id,
                artifact_ids={"readinessRunId": run.id},
            )
        if payload.action_type == OnboardingActionType.RUN_DEMO_FLOW:
            enabled, reason = demo_mode_availability(self.settings)
            if not enabled:
                raise AppError(403, "demo_mode_unavailable", reason or "Demo mode is unavailable")
            demo = await DemoModeService(self.session, self.settings).run_full_demo_flow(
                DemoModeRunRequest(
                    workspace_id=payload.workspace_id,
                    workspace_name=str(
                        payload.options.get("workspaceName")
                        or self.settings.demo_mode_default_workspace_name
                    ),
                )
            )
            return await self.response_with_status(
                payload,
                demo.status,
                demo.message,
                workspace_id=demo.workspace_id,
                user_id=demo.user_id,
                artifact_ids={
                    "sourceId": demo.source_id,
                    "watchlistId": demo.watchlist_id,
                    "scanConfigId": demo.scan_config_id,
                    "scanRunId": demo.scan_run_id,
                    "readinessRunId": demo.readiness_run_id,
                },
            )
        raise AppError(422, "unsupported_action", "Unsupported onboarding action")

    async def create_basic_watchlist(
        self,
        payload: OnboardingActionRequest,
    ) -> OnboardingActionResponse:
        workspace_id = await self.require_workspace_id(payload.workspace_id)
        symbols = await self.first_active_symbols()
        if not symbols:
            raise AppError(422, "symbols_required", "Seed symbols before creating a watchlist")
        source = await self.first_active_data_source(workspace_id)
        service = MarketScanService(self.session, self.settings)
        watchlist = await service.create_watchlist(
            WatchlistCreate(
                workspace_id=workspace_id,
                name=str(payload.options.get("name") or "Daily deterministic review"),
                description="Basic watchlist created from onboarding.",
                metadata_json={"createdBy": "onboarding"},
            )
        )
        item_ids: list[UUID] = []
        for symbol in symbols[:3]:
            item = await service.add_watchlist_item(
                watchlist.id,
                WatchlistItemCreate(
                    symbol_id=symbol.id,
                    source_id=source.id if source is not None else None,
                    timeframe=Timeframe.ONE_MINUTE,
                    include_partial_live_candle=False,
                    metadata_json={"createdBy": "onboarding"},
                ),
            )
            item_ids.append(item.id)
        return await self.response_with_status(
            payload,
            "completed",
            "Basic watchlist created.",
            workspace_id=workspace_id,
            artifact_ids={"watchlistId": watchlist.id, "watchlistItemIds": item_ids},
        )

    async def create_basic_scan_config(
        self,
        payload: OnboardingActionRequest,
    ) -> OnboardingActionResponse:
        workspace_id = await self.require_workspace_id(payload.workspace_id)
        service = MarketScanService(self.session, self.settings)
        watchlists = await service.list_watchlists(workspace_id, status=None, limit=50, offset=0)
        watchlist = next((item for item in watchlists if item.status == "active"), None)
        if watchlist is None:
            raise AppError(422, "watchlist_required", "Create a watchlist before scan config")
        source = await self.first_active_data_source(workspace_id)
        scan_config = await service.create_scan_config(
            ScheduledScanConfigCreate(
                workspace_id=workspace_id,
                name=str(payload.options.get("name") or "Daily deterministic scan"),
                description="Basic deterministic scan config created from onboarding.",
                watchlist_id=watchlist.id,
                source_id=source.id if source is not None else None,
                scan_mode=ScheduledScanMode.WATCHLIST,
                include_partial_live_candle=False,
                include_news_correlation=False,
                include_ai_explanation=False,
                include_reasoning=False,
                include_action_plan=False,
                metadata_json={"createdBy": "onboarding"},
            )
        )
        return await self.response_with_status(
            payload,
            "completed",
            "Basic scan config created.",
            workspace_id=workspace_id,
            artifact_ids={"scanConfigId": scan_config.id, "watchlistId": watchlist.id},
        )

    async def response_with_status(
        self,
        payload: OnboardingActionRequest,
        status: str,
        message: str,
        workspace_id: UUID | None = None,
        user_id: UUID | None = None,
        artifact_ids: dict[str, UUID | list[UUID] | None] | None = None,
    ) -> OnboardingActionResponse:
        selected_workspace_id = workspace_id or payload.workspace_id
        return OnboardingActionResponse(
            action_type=payload.action_type,
            status=status,
            message=message,
            workspace_id=selected_workspace_id,
            user_id=user_id or payload.user_id,
            artifact_ids=artifact_ids or {},
            onboarding_status=await self.get_status(
                selected_workspace_id, user_id or payload.user_id
            ),
        )

    async def require_workspace_id(self, workspace_id: UUID | None) -> UUID:
        workspace = await self.require_workspace(workspace_id)
        return workspace.id

    async def require_workspace(self, workspace_id: UUID | None) -> Workspace:
        workspace = await self.readiness_repository.get_workspace(workspace_id)
        if workspace is None:
            raise AppError(422, "workspace_required", "Create or select a workspace first")
        return workspace

    async def get_user(self, user_id: UUID | None, workspace_id: UUID | None) -> User | None:
        if user_id is not None:
            user = await self.session.get(User, user_id)
            if user is not None and (workspace_id is None or user.workspace_id == workspace_id):
                return user
            return None
        if workspace_id is None:
            return None
        result = await self.session.execute(
            select(User)
            .where(User.workspace_id == workspace_id)
            .order_by(User.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def first_active_symbols(self) -> list[Symbol]:
        result = await self.session.execute(
            select(Symbol).where(Symbol.is_active.is_(True)).order_by(Symbol.symbol.asc()).limit(3)
        )
        return list(result.scalars().all())

    async def first_active_data_source(self, workspace_id: UUID) -> DataSource | None:
        result = await self.session.execute(
            select(DataSource)
            .where(DataSource.workspace_id == workspace_id, DataSource.status == "active")
            .order_by(DataSource.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()


def count_status(payload: dict[str, object] | None, count_key: str) -> OnboardingCountStatus:
    metadata = payload.get("metadata", {}) if payload else {}
    count = int(metadata.get(count_key, 0)) if isinstance(metadata, dict) else 0
    configured = bool(payload and payload.get("status") == "passed")
    return OnboardingCountStatus(configured=configured, count=count, missing=not configured)


def data_source_status(payloads: dict[str, dict[str, object]]) -> OnboardingDataSourcesStatus:
    source = count_status(payloads.get("data_sources_present"), "active_data_source_count")
    credential = payloads.get("provider_credentials_status")
    provider_ready = (
        source.configured
        and credential is not None
        and credential.get("status")
        in {
            "passed",
            "warning",
            "skipped",
        }
    )
    return OnboardingDataSourcesStatus(
        configured=source.configured,
        count=source.count,
        missing=source.missing,
        provider_ready=provider_ready,
    )


def data_freshness_status(payload: dict[str, object] | None) -> OnboardingDataFreshnessStatus:
    if payload is None:
        return OnboardingDataFreshnessStatus(
            label=OnboardingDataFreshnessLabel.UNKNOWN,
            summary="Data freshness could not be checked.",
        )
    metadata = payload.get("metadata", {})
    candle_count = int(metadata.get("final_candle_count", 0)) if isinstance(metadata, dict) else 0
    status = str(payload.get("status") or "")
    if candle_count == 0:
        label = OnboardingDataFreshnessLabel.NO_DATA
    elif status == "passed":
        label = OnboardingDataFreshnessLabel.FRESH
    elif status == "warning":
        label = OnboardingDataFreshnessLabel.STALE
    else:
        label = OnboardingDataFreshnessLabel.UNKNOWN
    return OnboardingDataFreshnessStatus(label=label, summary=str(payload.get("summary") or ""))


def daily_workflow_status(payload: dict[str, object] | None) -> OnboardingDailyWorkflowStatus:
    metadata = payload.get("metadata", {}) if payload else {}
    return OnboardingDailyWorkflowStatus(
        available=payload is not None and payload.get("status") != "failed",
        last_run_status=str(metadata.get("latest_status"))
        if isinstance(metadata, dict) and metadata.get("latest_status")
        else None,
    )


def build_steps(
    *,
    workspace: bool,
    user: bool,
    symbols: bool,
    data_sources: bool,
    data_freshness: OnboardingDataFreshnessLabel,
    watchlists: bool,
    scan_configs: bool,
    readiness_label: str,
    demo_available: bool,
) -> list[OnboardingStep]:
    return [
        step(
            "workspace",
            "Workspace",
            "Create or select a workspace.",
            workspace,
            "/onboarding",
            OnboardingActionType.CREATE_WORKSPACE,
        ),
        step(
            "user",
            "Operator context",
            "Create an operator context for this workspace.",
            user,
            "/onboarding",
            OnboardingActionType.CREATE_USER,
        ),
        step(
            "symbols",
            "Symbols",
            "Seed default symbols for deterministic analysis.",
            symbols,
            "/data/onboarding",
            OnboardingActionType.SEED_SYMBOLS,
        ),
        step(
            "data_sources",
            "Data source",
            "Configure a source for candle data.",
            data_sources,
            "/data/onboarding",
            OnboardingActionType.SEED_DEFAULT_DATA_SOURCES,
        ),
        OnboardingStep(
            key="data_freshness",
            title="Data freshness",
            description="Import or refresh candles, then verify freshness explicitly.",
            state=OnboardingStepState.COMPLETE
            if data_freshness == OnboardingDataFreshnessLabel.FRESH
            else OnboardingStepState.WARNING
            if data_freshness == OnboardingDataFreshnessLabel.STALE
            else OnboardingStepState.INCOMPLETE,
            route="/data/onboarding",
        ),
        step(
            "watchlists",
            "Watchlist",
            "Create a watchlist for daily review.",
            watchlists,
            "/scanner",
            OnboardingActionType.CREATE_BASIC_WATCHLIST,
        ),
        step(
            "scan_configs",
            "Scan config",
            "Create a deterministic scan config.",
            scan_configs,
            "/scanner",
            OnboardingActionType.CREATE_BASIC_SCAN_CONFIG,
        ),
        OnboardingStep(
            key="daily_workflow",
            title="Daily workflow",
            description=(
                "Run deterministic daily workflow from the command center when setup is ready."
            ),
            state=OnboardingStepState.COMPLETE if scan_configs else OnboardingStepState.INCOMPLETE,
            route="/command-center",
        ),
        OnboardingStep(
            key="product_readiness",
            title="Product readiness",
            description="Run an explicit readiness check after setup changes.",
            state=OnboardingStepState.COMPLETE
            if readiness_label == "ready"
            else OnboardingStepState.WARNING
            if readiness_label == "degraded"
            else OnboardingStepState.INCOMPLETE,
            route="/readiness",
            action_type=OnboardingActionType.RUN_READINESS_CHECK,
        ),
        OnboardingStep(
            key="demo_mode",
            title="Demo workspace",
            description="Create labeled synthetic demo artifacts when demo mode is available.",
            state=OnboardingStepState.INCOMPLETE
            if demo_available
            else OnboardingStepState.UNAVAILABLE,
            route="/demo",
            action_type=OnboardingActionType.RUN_DEMO_FLOW if demo_available else None,
        ),
    ]


def step(
    key: str,
    title: str,
    description: str,
    complete: bool,
    route: str,
    action_type: OnboardingActionType | None = None,
) -> OnboardingStep:
    return OnboardingStep(
        key=key,
        title=title,
        description=description,
        state=OnboardingStepState.COMPLETE if complete else OnboardingStepState.INCOMPLETE,
        route=route,
        action_type=None if complete else action_type,
    )


def choose_next_step(
    *,
    workspace: bool,
    user: bool,
    symbols: bool,
    data_sources: bool,
    data_freshness: OnboardingDataFreshnessLabel,
    watchlists: bool,
    scan_configs: bool,
    readiness_label: str,
) -> OnboardingNextStep:
    if not workspace:
        return next_step(
            OnboardingNextStepKey.CREATE_WORKSPACE,
            "Create workspace",
            "Start with a workspace for deterministic analysis.",
            "/onboarding",
            OnboardingActionType.CREATE_WORKSPACE,
        )
    if not user:
        return next_step(
            OnboardingNextStepKey.CREATE_USER,
            "Create operator context",
            "Add an operator context to this workspace.",
            "/onboarding",
            OnboardingActionType.CREATE_USER,
        )
    if not symbols:
        return next_step(
            OnboardingNextStepKey.SEED_SYMBOLS,
            "Seed symbols",
            "Add default symbols before configuring data.",
            "/data/onboarding",
            OnboardingActionType.SEED_SYMBOLS,
        )
    if not data_sources:
        return next_step(
            OnboardingNextStepKey.CONFIGURE_DATA_SOURCE,
            "Configure data source",
            "Add a source so candles can be imported or checked.",
            "/data/onboarding",
            OnboardingActionType.SEED_DEFAULT_DATA_SOURCES,
        )
    if data_freshness != OnboardingDataFreshnessLabel.FRESH:
        return next_step(
            OnboardingNextStepKey.VERIFY_DATA,
            "Verify data",
            "Import candles or review freshness before daily analysis.",
            "/data/onboarding",
        )
    if not watchlists:
        return next_step(
            OnboardingNextStepKey.CREATE_WATCHLIST,
            "Create watchlist",
            "Create a watchlist for scanner and brief workflows.",
            "/scanner",
            OnboardingActionType.CREATE_BASIC_WATCHLIST,
        )
    if not scan_configs:
        return next_step(
            OnboardingNextStepKey.CREATE_SCAN_CONFIG,
            "Create scan config",
            "Create a deterministic scan config for the daily workflow.",
            "/scanner",
            OnboardingActionType.CREATE_BASIC_SCAN_CONFIG,
        )
    if readiness_label != "ready":
        return next_step(
            OnboardingNextStepKey.RUN_READINESS,
            "Run readiness",
            "Run the explicit product readiness check.",
            "/readiness",
            OnboardingActionType.RUN_READINESS_CHECK,
        )
    return next_step(
        OnboardingNextStepKey.OPEN_COMMAND_CENTER,
        "Open command center",
        "Command center is ready for deterministic analysis.",
        "/command-center",
    )


def next_step(
    key: OnboardingNextStepKey,
    title: str,
    description: str,
    route: str,
    action_type: OnboardingActionType | None = None,
) -> OnboardingNextStep:
    return OnboardingNextStep(
        key=key,
        title=title,
        description=description,
        route=route,
        action_type=action_type,
    )
