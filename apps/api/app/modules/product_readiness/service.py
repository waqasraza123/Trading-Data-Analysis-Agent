from decimal import Decimal
from uuid import UUID

from app.config import Settings, get_settings, provider_requires_api_key, secret_is_empty
from app.core.errors import AppError
from app.modules.live.operational import collect_live_worker_health
from app.modules.product_readiness.checks import (
    ProductReadinessCheckResult,
    known_alembic_heads,
    readiness_check,
    readiness_check_payload,
)
from app.modules.product_readiness.models import (
    ProductReadinessCheckStatus,
    ProductReadinessLabel,
    ProductReadinessRun,
    ProductReadinessRunStatus,
)
from app.modules.product_readiness.repository import ProductReadinessRepository
from app.modules.product_readiness.schemas import (
    ProductReadinessRunListResponse,
    ProductReadinessRunRead,
)

SETUP_CHECK_KEYS = {
    "seed_data_present",
    "workspace_present",
    "user_present",
    "symbols_present",
    "data_sources_present",
    "fresh_candles_available",
    "watchlist_configured",
    "scan_configured",
}
CRITICAL_CHECK_KEYS = {"api_health", "database_connection"}


class ProductReadinessService:
    def __init__(
        self, repository: ProductReadinessRepository, settings: Settings | None = None
    ) -> None:
        self.repository = repository
        self.settings = settings or get_settings()

    async def run_readiness_check(
        self,
        workspace_id: UUID | None = None,
    ) -> ProductReadinessRunRead:
        workspace = await self.repository.get_workspace(workspace_id)
        selected_workspace_id = workspace.id if workspace is not None else None
        checks = await self.build_checks(workspace_id, selected_workspace_id)
        blockers = [
            readiness_check_payload(check)
            for check in checks
            if check.status == ProductReadinessCheckStatus.FAILED
        ]
        warnings = [
            readiness_check_payload(check)
            for check in checks
            if check.status == ProductReadinessCheckStatus.WARNING
        ]
        readiness_score = calculate_readiness_score(checks)
        readiness_label = choose_readiness_label(checks)
        status = choose_run_status(checks)
        summary = summarize_readiness(readiness_label, blockers, warnings)
        run = await self.repository.create_run(
            ProductReadinessRun(
                workspace_id=selected_workspace_id,
                status=status.value,
                readiness_version=self.settings.product_readiness_version,
                readiness_score=Decimal(str(readiness_score)).quantize(Decimal("0.0001")),
                readiness_label=readiness_label.value,
                summary=summary,
                checks_json=[readiness_check_payload(check) for check in checks],
                blockers_json=blockers,
                warnings_json=warnings,
            )
        )
        await self.repository.session.commit()
        return ProductReadinessRunRead.model_validate(run)

    async def get_latest_readiness(
        self,
        workspace_id: UUID | None = None,
    ) -> ProductReadinessRunRead:
        run = await self.repository.get_latest(workspace_id)
        if run is None:
            raise AppError(404, "product_readiness_not_found", "No product readiness run exists")
        return ProductReadinessRunRead.model_validate(run)

    async def get_readiness_run(self, run_id: UUID) -> ProductReadinessRunRead:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise AppError(
                404, "product_readiness_not_found", "Product readiness run was not found"
            )
        return ProductReadinessRunRead.model_validate(run)

    async def list_readiness_runs(
        self,
        workspace_id: UUID | None,
        limit: int,
        offset: int,
        readiness_label: str | None = None,
        status: str | None = None,
    ) -> ProductReadinessRunListResponse:
        runs = await self.repository.list_runs(
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
            readiness_label=readiness_label,
            status=status,
        )
        return ProductReadinessRunListResponse(
            runs=[ProductReadinessRunRead.model_validate(run) for run in runs]
        )

    async def build_checks(
        self,
        requested_workspace_id: UUID | None,
        workspace_id: UUID | None,
    ) -> list[ProductReadinessCheckResult]:
        checks = [
            await self.check_api_health(),
            await self.check_database_connection(),
            await self.check_migration_head_known(),
            await self.check_workspace_present(requested_workspace_id, workspace_id),
            await self.check_user_present(workspace_id),
            await self.check_symbols_present(),
            await self.check_data_sources_present(workspace_id),
            await self.check_seed_data_present(workspace_id),
            await self.check_provider_credentials_status(workspace_id),
            await self.check_provider_health_available(workspace_id),
            await self.check_read_model_availability(workspace_id),
            await self.check_fresh_candles_available(workspace_id),
            await self.check_watchlist_configured(workspace_id),
            await self.check_scan_configured(workspace_id),
            await self.check_daily_workflow_available(workspace_id),
            await self.check_runtime_supervisor_status(workspace_id),
            await self.check_worker_health_available(),
            await self.check_notification_channels_optional(workspace_id),
            await self.check_journal_available(workspace_id),
            await self.check_web_api_configured(),
            await self.check_no_critical_stale_or_missing_data(workspace_id),
        ]
        return checks

    async def check_api_health(self) -> ProductReadinessCheckResult:
        return readiness_check(
            key="api_health",
            status=ProductReadinessCheckStatus.PASSED,
            title="API reachable",
            summary="The readiness service is responding inside the API process.",
            remediation="Start the FastAPI app and verify /health if this check fails.",
            related_route="/health",
            metadata={
                "service": self.settings.service_name,
                "environment": self.settings.app_env.value,
            },
        )

    async def check_database_connection(self) -> ProductReadinessCheckResult:
        connected = await self.repository.check_database_connection()
        return readiness_check(
            key="database_connection",
            status=(
                ProductReadinessCheckStatus.PASSED
                if connected
                else ProductReadinessCheckStatus.FAILED
            ),
            title="Database configured",
            summary=(
                "The API can execute a database query."
                if connected
                else "The API could not execute a database query."
            ),
            remediation="Configure DATABASE_URL and run migrations before daily use.",
            related_route="/health/db",
            metadata={"database_url_configured": self.settings.database_url is not None},
        )

    async def check_migration_head_known(self) -> ProductReadinessCheckResult:
        database_versions, version_table_found = await self.repository.get_alembic_versions()
        if not version_table_found:
            return readiness_check(
                key="migration_head_known",
                status=ProductReadinessCheckStatus.SKIPPED,
                title="Migration head known",
                summary="The Alembic version table is not detectable in this database.",
                remediation="Run Alembic migrations and verify the alembic_version table.",
                related_route="/health/db",
                metadata={},
            )
        code_heads = known_alembic_heads()
        if code_heads is None:
            return readiness_check(
                key="migration_head_known",
                status=ProductReadinessCheckStatus.WARNING,
                title="Migration head known",
                summary=(
                    "Database migration versions exist, but the code migration head could not "
                    "be detected."
                ),
                remediation="Verify migrations with alembic heads and alembic current.",
                related_route="/health/db",
                metadata={"database_versions": database_versions},
            )
        status = (
            ProductReadinessCheckStatus.PASSED
            if set(database_versions) == set(code_heads)
            else ProductReadinessCheckStatus.WARNING
        )
        return readiness_check(
            key="migration_head_known",
            status=status,
            title="Migration head known",
            summary=(
                "Database migration head matches the installed Alembic head."
                if status == ProductReadinessCheckStatus.PASSED
                else "Database migration head does not match the installed Alembic head."
            ),
            remediation="Run alembic upgrade head against the configured database.",
            related_route="/health/db",
            metadata={"database_versions": database_versions, "code_heads": code_heads},
        )

    async def check_workspace_present(
        self,
        requested_workspace_id: UUID | None,
        workspace_id: UUID | None,
    ) -> ProductReadinessCheckResult:
        workspace_count = await self.repository.count_workspaces()
        passed = workspace_id is not None or workspace_count > 0
        summary = "A workspace is available for readiness checks."
        if requested_workspace_id is not None and workspace_id is None:
            summary = "The requested workspace does not exist."
        elif not passed:
            summary = "No workspace exists."
        return readiness_check(
            key="workspace_present",
            status=ProductReadinessCheckStatus.PASSED
            if passed
            else ProductReadinessCheckStatus.FAILED,
            title="Workspace exists",
            summary=summary,
            remediation="Seed or create a workspace before using daily review workflows.",
            related_route="/command-center",
            metadata={
                "workspace_count": workspace_count,
                "selected_workspace_id": str(workspace_id) if workspace_id is not None else None,
            },
        )

    async def check_user_present(self, workspace_id: UUID | None) -> ProductReadinessCheckResult:
        if workspace_id is None:
            return readiness_check(
                key="user_present",
                status=ProductReadinessCheckStatus.SKIPPED,
                title="User exists",
                summary="User readiness is workspace-scoped and no workspace is selected.",
                remediation="Create or select a workspace, then create an operator user.",
                related_route="/preferences/strategy",
            )
        count = await self.repository.count_users(workspace_id)
        return readiness_check(
            key="user_present",
            status=ProductReadinessCheckStatus.PASSED
            if count > 0
            else ProductReadinessCheckStatus.FAILED,
            title="User exists",
            summary="At least one user exists for this workspace."
            if count
            else "No user exists for this workspace.",
            remediation="Seed or create an operator user for this workspace.",
            related_route="/preferences/strategy",
            metadata={"user_count": count},
        )

    async def check_symbols_present(self) -> ProductReadinessCheckResult:
        count = await self.repository.count_active_symbols()
        return readiness_check(
            key="symbols_present",
            status=ProductReadinessCheckStatus.PASSED
            if count > 0
            else ProductReadinessCheckStatus.FAILED,
            title="Symbols exist",
            summary="Active symbols are available."
            if count
            else "No active symbols are available.",
            remediation="Seed default symbols or create symbols before onboarding data.",
            related_route="/data/onboarding",
            metadata={"active_symbol_count": count},
        )

    async def check_data_sources_present(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        if workspace_id is None:
            return readiness_check(
                key="data_sources_present",
                status=ProductReadinessCheckStatus.SKIPPED,
                title="Data sources exist",
                summary="Data source readiness is workspace-scoped and no workspace is selected.",
                remediation="Create or select a workspace, then configure a data source.",
                related_route="/data/onboarding",
            )
        count = await self.repository.count_active_data_sources(workspace_id)
        return readiness_check(
            key="data_sources_present",
            status=ProductReadinessCheckStatus.PASSED
            if count > 0
            else ProductReadinessCheckStatus.FAILED,
            title="Data sources exist",
            summary="Active data sources are configured."
            if count
            else "No active data source is configured.",
            remediation="Create a CSV, JSON, manual, polling, or live data source.",
            related_route="/data/onboarding",
            metadata={"active_data_source_count": count},
        )

    async def check_seed_data_present(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        counts = await self.repository.count_seed_records(workspace_id)
        missing = [key for key, count in counts.items() if count == 0]
        return readiness_check(
            key="seed_data_present",
            status=ProductReadinessCheckStatus.PASSED
            if not missing
            else ProductReadinessCheckStatus.WARNING,
            title="Seed data exists",
            summary=(
                "Core seed data exists."
                if not missing
                else f"Some seed-backed records are missing: {', '.join(missing)}."
            ),
            remediation=(
                "Run the backend seed command for default symbols, sources, profiles, engines, "
                "and presets."
            ),
            related_route="/data/onboarding",
            metadata=counts,
        )

    async def check_provider_credentials_status(
        self,
        workspace_id: UUID | None,
    ) -> ProductReadinessCheckResult:
        missing: list[str] = []
        if provider_requires_api_key(self.settings.live_feed_provider) and secret_is_empty(
            self.settings.live_feed_api_key
        ):
            missing.append("LIVE_FEED_API_KEY")
        if (
            self.settings.llm_explanations_enabled
            and self.settings.llm_provider == "openai"
            and secret_is_empty(self.settings.openai_api_key)
        ):
            missing.append("OPENAI_API_KEY")
        if (
            self.settings.llm_reasoning_enabled
            and self.settings.llm_default_provider == "anthropic"
            and secret_is_empty(self.settings.anthropic_api_key)
        ):
            missing.append("ANTHROPIC_API_KEY")
        credential_count = await self.repository.count_provider_credential_refs(workspace_id)
        status_counts = await self.repository.provider_credential_status_counts(workspace_id)
        test_status_counts = await self.repository.provider_credential_test_status_counts(
            workspace_id
        )
        failed_count = status_counts.get("test_failed", 0) + test_status_counts.get("failed", 0)
        needs_review_count = (
            status_counts.get("missing", 0)
            + status_counts.get("paused", 0)
            + status_counts.get("revoked", 0)
            + test_status_counts.get("provider_not_configured", 0)
        )
        if missing or failed_count:
            status = ProductReadinessCheckStatus.FAILED
        elif credential_count == 0 or needs_review_count:
            status = ProductReadinessCheckStatus.WARNING
        else:
            status = ProductReadinessCheckStatus.PASSED
        return readiness_check(
            key="provider_credentials_status",
            status=status,
            title="Provider credentials configured where needed",
            summary=provider_credential_summary(
                missing=missing,
                credential_count=credential_count,
                failed_count=failed_count,
                needs_review_count=needs_review_count,
            ),
            remediation=(
                "Configure server-side credential references only for enabled data and delivery "
                "providers."
            ),
            related_route="/data/onboarding",
            metadata={
                "missing_settings": missing,
                "live_feed_provider": self.settings.live_feed_provider,
                "credential_ref_count": credential_count,
                "credential_status_counts": status_counts,
                "credential_test_status_counts": test_status_counts,
            },
        )

    async def check_provider_health_available(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        count = await self.repository.count_provider_health_snapshots(workspace_id)
        return readiness_check(
            key="provider_health_available",
            status=ProductReadinessCheckStatus.PASSED
            if count > 0
            else ProductReadinessCheckStatus.WARNING,
            title="Provider health available",
            summary=(
                "Provider health snapshots are available."
                if count
                else "No provider health snapshot has been recorded yet."
            ),
            remediation=(
                "Use data onboarding or an explicit daily workflow run to refresh provider health."
            ),
            related_route="/data/onboarding",
            metadata={"snapshot_count": count},
        )

    async def check_read_model_availability(
        self,
        workspace_id: UUID | None,
    ) -> ProductReadinessCheckResult:
        counts = await self.repository.read_model_counts(workspace_id)
        total_count = sum(counts.values())
        return readiness_check(
            key="read_model_availability",
            status=ProductReadinessCheckStatus.PASSED
            if total_count
            else ProductReadinessCheckStatus.WARNING,
            title="Read models available",
            summary=(
                "Dashboard read model snapshots are available."
                if total_count
                else "Dashboard read model snapshots have not been materialized yet."
            ),
            remediation=(
                "Run explicit read model rebuild endpoints or a workflow step after source "
                "artifacts are available."
            ),
            related_route="/command-center",
            metadata={**counts, "read_model_version": self.settings.read_model_version},
        )

    async def check_fresh_candles_available(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        candle_count = await self.repository.count_final_candles(workspace_id)
        latest = await self.repository.get_latest_final_candle_time(workspace_id)
        provider_freshness = await self.repository.provider_health_freshness_counts(workspace_id)
        memory_freshness = await self.repository.market_memory_freshness_counts(workspace_id)
        fresh_count = provider_freshness.get("fresh", 0) + memory_freshness.get("fresh", 0)
        delayed_count = provider_freshness.get("delayed", 0) + memory_freshness.get("delayed", 0)
        stale_count = provider_freshness.get("stale", 0) + memory_freshness.get("stale", 0)
        no_data_count = provider_freshness.get("no_data", 0) + memory_freshness.get("no_data", 0)
        if candle_count == 0:
            status = ProductReadinessCheckStatus.FAILED
            summary = "No final candles are available."
        elif fresh_count or delayed_count:
            status = ProductReadinessCheckStatus.PASSED
            summary = "Final candles and freshness context are available."
        elif stale_count or no_data_count:
            status = ProductReadinessCheckStatus.WARNING
            summary = "Final candles exist, but freshness context reports stale or missing data."
        else:
            status = ProductReadinessCheckStatus.WARNING
            summary = "Final candles exist, but freshness context has not been recorded."
        return readiness_check(
            key="fresh_candles_available",
            status=status,
            title="Fresh candle data available",
            summary=summary,
            remediation="Import candles or explicitly refresh provider health before daily review.",
            related_route="/data/onboarding",
            metadata={
                "final_candle_count": candle_count,
                "latest_final_candle_time": latest.isoformat() if latest is not None else None,
                "provider_freshness": provider_freshness,
                "market_memory_freshness": memory_freshness,
            },
        )

    async def check_watchlist_configured(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        watchlist_count = await self.repository.count_active_watchlists(workspace_id)
        item_count = await self.repository.count_active_watchlist_items(workspace_id)
        passed = watchlist_count > 0 and item_count > 0
        return readiness_check(
            key="watchlist_configured",
            status=ProductReadinessCheckStatus.PASSED
            if passed
            else ProductReadinessCheckStatus.FAILED,
            title="Watchlist configured",
            summary=(
                "An active watchlist with active items exists."
                if passed
                else "No active watchlist with active items is configured."
            ),
            remediation="Create a watchlist and add symbols/timeframes in the scanner.",
            related_route="/scanner",
            metadata={"active_watchlists": watchlist_count, "active_watchlist_items": item_count},
        )

    async def check_scan_configured(self, workspace_id: UUID | None) -> ProductReadinessCheckResult:
        count = await self.repository.count_active_scan_configs(workspace_id)
        return readiness_check(
            key="scan_configured",
            status=ProductReadinessCheckStatus.PASSED
            if count > 0
            else ProductReadinessCheckStatus.FAILED,
            title="Scan config exists",
            summary="An active scan config exists." if count else "No active scan config exists.",
            remediation="Create a scheduled scan config or apply a scanner preset.",
            related_route="/scanner",
            metadata={"active_scan_config_count": count},
        )

    async def check_daily_workflow_available(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        count = await self.repository.count_daily_workflow_runs(workspace_id)
        latest_status = await self.repository.latest_daily_workflow_status(workspace_id)
        return readiness_check(
            key="daily_workflow_available",
            status=ProductReadinessCheckStatus.PASSED,
            title="Daily workflow can run",
            summary=(
                "Daily workflow persistence is available."
                if count == 0
                else "Daily workflow persistence is available and previous runs exist."
            ),
            remediation="Run the daily workflow explicitly from Command Center when ready.",
            related_route="/command-center",
            metadata={"run_count": count, "latest_status": latest_status},
        )

    async def check_runtime_supervisor_status(
        self,
        workspace_id: UUID | None,
    ) -> ProductReadinessCheckResult:
        definition_count = await self.repository.count_runtime_worker_definitions()
        definition_statuses = await self.repository.runtime_worker_definition_status_counts()
        instance_statuses = await self.repository.runtime_worker_instance_status_counts(
            workspace_id
        )
        request_statuses = await self.repository.runtime_run_request_status_counts(workspace_id)
        degraded_count = (
            instance_statuses.get("failed", 0)
            + instance_statuses.get("stale", 0)
            + request_statuses.get("failed", 0)
        )
        status = (
            ProductReadinessCheckStatus.WARNING
            if definition_count == 0 or degraded_count
            else ProductReadinessCheckStatus.PASSED
        )
        return readiness_check(
            key="runtime_supervisor_status",
            status=status,
            title="Runtime supervisor status available",
            summary=(
                "Runtime supervisor definitions and persisted status are available."
                if status == ProductReadinessCheckStatus.PASSED
                else "Runtime supervisor status needs review before relying on worker state."
            ),
            remediation=(
                "Seed default worker definitions and inspect runtime status before operating "
                "scheduled workers."
            ),
            related_route="/command-center",
            metadata={
                "definition_count": definition_count,
                "definition_status_counts": definition_statuses,
                "instance_status_counts": instance_statuses,
                "run_request_status_counts": request_statuses,
                "supervisor_version": self.settings.runtime_supervisor_version,
                "heartbeat_enabled": self.settings.runtime_worker_heartbeat_enabled,
                "run_requests_enabled": self.settings.runtime_supervisor_run_requests_enabled,
            },
        )

    async def check_worker_health_available(self) -> ProductReadinessCheckResult:
        live_worker_health = await collect_live_worker_health(self.repository.session)
        status = (
            ProductReadinessCheckStatus.WARNING
            if live_worker_health.status in {"degraded", "not_running"}
            and live_worker_health.active_subscriptions
            else ProductReadinessCheckStatus.PASSED
        )
        return readiness_check(
            key="worker_health_available",
            status=status,
            title="Workers and runtime status available",
            summary="Worker health can be inspected from persisted runtime state.",
            remediation=(
                "Start the relevant worker process only when live or scheduled workers are "
                "intended."
            ),
            related_route="/health/workers",
            metadata={
                "live_feed_worker": live_worker_health.model_dump(),
                "notification_worker_enabled": self.settings.notification_worker_enabled,
                "market_scan_worker_enabled": self.settings.market_scan_worker_enabled,
                "reasoning_action_worker_enabled": self.settings.reasoning_action_worker_enabled,
            },
        )

    async def check_notification_channels_optional(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        active_channels = await self.repository.count_notification_channels(workspace_id)
        worker_runs = await self.repository.count_notification_worker_runs(workspace_id)
        if not self.settings.notifications_enabled:
            status = ProductReadinessCheckStatus.SKIPPED
            summary = "Notifications are disabled by default and are optional for readiness."
        elif active_channels:
            status = ProductReadinessCheckStatus.PASSED
            summary = "Notifications are enabled and active channels exist."
        else:
            status = ProductReadinessCheckStatus.WARNING
            summary = "Notifications are enabled, but no active delivery channel exists."
        return readiness_check(
            key="notification_channels_optional",
            status=status,
            title="Notifications configured if desired",
            summary=summary,
            remediation=(
                "Keep notifications disabled, or explicitly configure channels before enabling "
                "delivery."
            ),
            related_route="/notifications",
            metadata={
                "notifications_enabled": self.settings.notifications_enabled,
                "active_channel_count": active_channels,
                "worker_run_count": worker_runs,
            },
        )

    async def check_journal_available(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        count = await self.repository.count_journal_entries(workspace_id)
        return readiness_check(
            key="journal_available",
            status=ProductReadinessCheckStatus.PASSED,
            title="Journal ready",
            summary="Journal persistence is available for operator notes.",
            remediation="Use the journal after reviewing setups or observed outcomes.",
            related_route="/journal",
            metadata={"journal_entry_count": count},
        )

    async def check_web_api_configured(self) -> ProductReadinessCheckResult:
        cors_configured = bool(self.settings.cors_allowed_origins)
        return readiness_check(
            key="web_api_configured",
            status=ProductReadinessCheckStatus.PASSED
            if cors_configured
            else ProductReadinessCheckStatus.WARNING,
            title="Web app can reach API",
            summary=(
                "CORS origins are configured for browser-side API calls."
                if cors_configured
                else "The API is reachable, but CORS origins are not configured."
            ),
            remediation=(
                "Set NEXT_PUBLIC_API_BASE_URL in the web app and configure CORS_ALLOWED_ORIGINS "
                "when the browser calls this API across origins."
            ),
            related_route="/readiness",
            metadata={
                "api_prefix": self.settings.api_prefix,
                "cors_allowed_origins": self.settings.cors_allowed_origins,
            },
        )

    async def check_no_critical_stale_or_missing_data(
        self, workspace_id: UUID | None
    ) -> ProductReadinessCheckResult:
        provider_statuses = await self.repository.provider_health_status_counts(workspace_id)
        provider_freshness = await self.repository.provider_health_freshness_counts(workspace_id)
        memory_quality = await self.repository.market_memory_quality_counts(workspace_id)
        finding_counts = await self.repository.data_quality_finding_counts(workspace_id)
        data_quality_runs = await self.repository.count_data_quality_runs(workspace_id)
        critical_status_count = sum(
            provider_statuses.get(key, 0) for key in ("failing", "unavailable")
        )
        stale_count = provider_statuses.get("stale", 0) + provider_freshness.get("stale", 0)
        missing_count = provider_freshness.get("no_data", 0)
        poor_memory_count = memory_quality.get("poor", 0) + memory_quality.get("insufficient", 0)
        high_findings = finding_counts.get("high", 0)
        if critical_status_count or poor_memory_count or high_findings:
            status = ProductReadinessCheckStatus.FAILED
            summary = "Critical stale, missing, or poor-quality data signals are present."
        elif stale_count or missing_count:
            status = ProductReadinessCheckStatus.WARNING
            summary = "Some stale or missing data warnings are present."
        else:
            status = ProductReadinessCheckStatus.PASSED
            summary = "No critical stale or missing data indicators were found."
        return readiness_check(
            key="no_critical_stale_or_missing_data",
            status=status,
            title="No critical stale or missing data",
            summary=summary,
            remediation=(
                "Use data onboarding to inspect freshness, quality findings, and gap recovery "
                "plans."
            ),
            related_route="/data/onboarding",
            metadata={
                "provider_statuses": provider_statuses,
                "provider_freshness": provider_freshness,
                "market_memory_quality": memory_quality,
                "data_quality_finding_counts": finding_counts,
                "data_quality_run_count": data_quality_runs,
            },
        )


def calculate_readiness_score(checks: list[ProductReadinessCheckResult]) -> float:
    if not checks:
        return 0.0
    weights = {
        ProductReadinessCheckStatus.PASSED: 1.0,
        ProductReadinessCheckStatus.WARNING: 0.5,
        ProductReadinessCheckStatus.SKIPPED: 0.5,
        ProductReadinessCheckStatus.FAILED: 0.0,
    }
    return round(sum(weights[check.status] for check in checks) / len(checks), 4)


def choose_run_status(checks: list[ProductReadinessCheckResult]) -> ProductReadinessRunStatus:
    if any(check.status == ProductReadinessCheckStatus.FAILED for check in checks):
        return ProductReadinessRunStatus.FAILED
    if any(
        check.status in {ProductReadinessCheckStatus.WARNING, ProductReadinessCheckStatus.SKIPPED}
        for check in checks
    ):
        return ProductReadinessRunStatus.COMPLETED_WITH_WARNINGS
    return ProductReadinessRunStatus.COMPLETED


def choose_readiness_label(checks: list[ProductReadinessCheckResult]) -> ProductReadinessLabel:
    failed_keys = {
        check.key for check in checks if check.status == ProductReadinessCheckStatus.FAILED
    }
    warning_exists = any(check.status == ProductReadinessCheckStatus.WARNING for check in checks)
    if failed_keys & CRITICAL_CHECK_KEYS:
        return ProductReadinessLabel.BLOCKED
    if failed_keys & SETUP_CHECK_KEYS:
        return ProductReadinessLabel.NEEDS_SETUP
    if failed_keys:
        return ProductReadinessLabel.BLOCKED
    if warning_exists:
        return ProductReadinessLabel.DEGRADED
    if checks:
        return ProductReadinessLabel.READY
    return ProductReadinessLabel.UNKNOWN


def summarize_readiness(
    label: ProductReadinessLabel,
    blockers: list[dict[str, object]],
    warnings: list[dict[str, object]],
) -> str:
    if label == ProductReadinessLabel.READY:
        return "Product readiness checks passed for daily operator use."
    if label == ProductReadinessLabel.NEEDS_SETUP:
        return f"Product readiness needs setup before daily use: {len(blockers)} blocker(s)."
    if label == ProductReadinessLabel.DEGRADED:
        return f"Product readiness is degraded: {len(warnings)} warning(s) require review."
    if label == ProductReadinessLabel.BLOCKED:
        return f"Product readiness is blocked: {len(blockers)} blocker(s) require remediation."
    return "Product readiness could not be determined."


def provider_credential_summary(
    *,
    missing: list[str],
    credential_count: int,
    failed_count: int,
    needs_review_count: int,
) -> str:
    if missing:
        return "One or more enabled providers are missing required credential settings."
    if failed_count:
        return "One or more provider credential references have failing connection tests."
    if credential_count == 0:
        return "No persisted provider credential references have been configured."
    if needs_review_count:
        return "One or more provider credential references need operator review."
    return "Provider credential references are configured where needed."
