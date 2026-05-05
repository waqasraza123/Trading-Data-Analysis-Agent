from dataclasses import dataclass
from importlib.util import find_spec

from app.config import Settings, WorkerSupervisorComponent
from app.modules.runtime_supervisor.models import (
    RuntimeWorkerDefinitionStatus,
    RuntimeWorkerType,
)


@dataclass(frozen=True)
class RuntimeWorkerDefinitionSpec:
    key: str
    name: str
    description: str
    worker_type: RuntimeWorkerType
    status: RuntimeWorkerDefinitionStatus
    command: str
    required_settings: tuple[str, ...]
    optional_settings: tuple[str, ...]
    safety_notes: tuple[str, ...]
    metadata: dict[str, object]


def default_worker_definitions(settings: Settings) -> list[RuntimeWorkerDefinitionSpec]:
    definitions = [
        RuntimeWorkerDefinitionSpec(
            key="live_feed_worker",
            name="Live feed worker",
            description=(
                "Maintains configured live feed subscriptions and writes normalized candle events."
            ),
            worker_type=RuntimeWorkerType.LIVE_FEED,
            status=available_if_module("app.workers.live_feed_worker"),
            command="python -m app.workers.live_feed_worker",
            required_settings=("DATABASE_URL",),
            optional_settings=(
                "LIVE_FEED_PROVIDER",
                "LIVE_FEED_API_KEY",
                "LIVE_FEED_WORKER_POLL_SECONDS",
            ),
            safety_notes=(
                "Backend data ingestion only.",
                "Does not execute broker actions.",
                "Does not create trading advice.",
            ),
            metadata={
                "enabledBySupervisorComponent": worker_component_enabled(
                    settings,
                    WorkerSupervisorComponent.LIVE_FEED,
                ),
                "heartbeatSupported": True,
            },
        ),
        RuntimeWorkerDefinitionSpec(
            key="live_stale_monitor",
            name="Live stale monitor",
            description=(
                "Marks live feed subscriptions stale when feed or final candle activity expires."
            ),
            worker_type=RuntimeWorkerType.STALE_MONITOR,
            status=available_if_module("app.workers.stale_monitor_worker"),
            command="python -m app.workers.stale_monitor_worker",
            required_settings=("DATABASE_URL",),
            optional_settings=(
                "LIVE_FEED_STALE_MESSAGE_SECONDS",
                "LIVE_FEED_STALE_FINAL_CANDLE_SECONDS",
            ),
            safety_notes=(
                "Updates operational live subscription state only.",
                "Does not execute broker actions.",
                "Does not alter signal classification.",
            ),
            metadata={
                "enabledBySupervisorComponent": worker_component_enabled(
                    settings,
                    WorkerSupervisorComponent.STALE_MONITOR,
                ),
                "heartbeatSupported": True,
            },
        ),
        RuntimeWorkerDefinitionSpec(
            key="reasoning_actions_worker",
            name="Reasoning actions worker",
            description=(
                "Executes due backend-safe reasoning action items through existing action runner."
            ),
            worker_type=RuntimeWorkerType.REASONING_ACTIONS,
            status=enabled_module_status(
                "app.workers.reasoning_actions_worker",
                settings.reasoning_action_worker_enabled,
            ),
            command="python -m app.workers.reasoning_actions_worker",
            required_settings=("DATABASE_URL",),
            optional_settings=(
                "REASONING_ACTION_WORKER_ENABLED",
                "REASONING_ACTION_WORKER_BATCH_SIZE",
                "REASONING_ACTION_WORKER_POLL_SECONDS",
            ),
            safety_notes=(
                "Executes only validated backend-safe action items.",
                "Does not execute broker actions.",
                "Does not provide financial advice.",
            ),
            metadata={
                "enabled": settings.reasoning_action_worker_enabled,
                "enabledBySupervisorComponent": worker_component_enabled(
                    settings,
                    WorkerSupervisorComponent.REASONING_ACTIONS,
                ),
                "heartbeatSupported": True,
                "safeRunRequestTypes": ("execute_due", "dry_run"),
            },
        ),
        RuntimeWorkerDefinitionSpec(
            key="market_scan_worker",
            name="Market scan worker",
            description=(
                "Executes due deterministic scheduled scan configurations over stored candles."
            ),
            worker_type=RuntimeWorkerType.MARKET_SCANS,
            status=enabled_module_status(
                "app.workers.market_scan_worker",
                settings.market_scan_worker_enabled,
            ),
            command="python -m app.workers.market_scan_worker",
            required_settings=("DATABASE_URL",),
            optional_settings=(
                "MARKET_SCAN_WORKER_ENABLED",
                "MARKET_SCAN_WORKER_BATCH_SIZE",
                "MARKET_SCAN_WORKER_POLL_SECONDS",
            ),
            safety_notes=(
                "Runs deterministic analysis over stored data.",
                "Does not send notifications or broker actions.",
                "Does not execute external provider polling.",
            ),
            metadata={
                "enabled": settings.market_scan_worker_enabled,
                "enabledBySupervisorComponent": worker_component_enabled(
                    settings,
                    WorkerSupervisorComponent.MARKET_SCANS,
                ),
                "heartbeatSupported": True,
                "safeRunRequestTypes": ("execute_due", "dry_run"),
            },
        ),
        RuntimeWorkerDefinitionSpec(
            key="provider_polling_operations",
            name="Provider polling operations",
            description="Tracks explicit provider polling requests created through existing APIs.",
            worker_type=RuntimeWorkerType.PROVIDER_POLLING,
            status=available_if_module("app.modules.provider_polling.service"),
            command="api: /provider-polling",
            required_settings=("DATABASE_URL",),
            optional_settings=(
                "PROVIDER_POLLING_TIMEOUT_SECONDS",
                "PROVIDER_POLLING_MAX_CANDLES_PER_REQUEST",
            ),
            safety_notes=(
                "Run requests are recorded only in the runtime supervisor.",
                "External provider calls remain behind explicit provider polling APIs.",
                "Does not execute broker actions.",
            ),
            metadata={"heartbeatSupported": False},
        ),
    ]
    definitions.extend(optional_definition_specs(settings))
    return definitions


def optional_definition_specs(settings: Settings) -> list[RuntimeWorkerDefinitionSpec]:
    definitions: list[RuntimeWorkerDefinitionSpec] = []
    if module_exists("app.workers.notification_worker"):
        definitions.append(
            RuntimeWorkerDefinitionSpec(
                key="notification_delivery_worker",
                name="Notification delivery worker",
                description=(
                    "Dispatches due notification events through existing delivery services."
                ),
                worker_type=RuntimeWorkerType.NOTIFICATION_DELIVERY,
                status=enabled_module_status(
                    "app.workers.notification_worker",
                    settings.notification_worker_enabled,
                ),
                command="python -m app.workers.notification_worker",
                required_settings=("DATABASE_URL",),
                optional_settings=(
                    "NOTIFICATION_WORKER_ENABLED",
                    "NOTIFICATIONS_ENABLED",
                    "NOTIFICATION_WORKER_BATCH_SIZE",
                ),
                safety_notes=(
                    "Uses existing notification safety filters.",
                    "Must not become trading alerts.",
                    "Does not execute broker actions.",
                ),
                metadata={
                    "enabled": settings.notification_worker_enabled,
                    "enabledBySupervisorComponent": worker_component_enabled(
                        settings,
                        WorkerSupervisorComponent.NOTIFICATIONS,
                    ),
                    "heartbeatSupported": True,
                    "safeRunRequestTypes": ("execute_due", "dry_run"),
                },
            )
        )
    if module_exists("app.modules.data_retention.service"):
        definitions.append(
            RuntimeWorkerDefinitionSpec(
                key="data_retention_worker",
                name="Data retention worker",
                description="Tracks data retention planning and apply operations.",
                worker_type=RuntimeWorkerType.DATA_RETENTION,
                status=RuntimeWorkerDefinitionStatus.AVAILABLE,
                command="api: /data-retention",
                required_settings=("DATABASE_URL",),
                optional_settings=(),
                safety_notes=(
                    "Runtime supervisor run requests are record-only.",
                    "Destructive retention apply remains behind explicit retention APIs.",
                ),
                metadata={"heartbeatSupported": False},
            )
        )
    if module_exists("app.modules.intelligence_metrics.service"):
        definitions.append(
            RuntimeWorkerDefinitionSpec(
                key="metrics_snapshot_worker",
                name="Metrics snapshot worker",
                description="Tracks intelligence metrics snapshot collection operations.",
                worker_type=RuntimeWorkerType.METRICS,
                status=RuntimeWorkerDefinitionStatus.AVAILABLE,
                command="api: /intelligence-metrics",
                required_settings=("DATABASE_URL",),
                optional_settings=(),
                safety_notes=(
                    "Runtime supervisor run requests are record-only.",
                    "Metrics snapshots are operational counters only.",
                ),
                metadata={"heartbeatSupported": False},
            )
        )
    if module_exists("app.modules.backfill_plans.service"):
        definitions.append(
            RuntimeWorkerDefinitionSpec(
                key="backfill_worker",
                name="Backfill worker",
                description="Tracks dry-run intelligence backfill plan operations.",
                worker_type=RuntimeWorkerType.BACKFILL,
                status=RuntimeWorkerDefinitionStatus.AVAILABLE,
                command="api: /backfill-plans",
                required_settings=("DATABASE_URL",),
                optional_settings=("BACKFILL_PLAN_DEFAULT_LIMIT", "BACKFILL_PLAN_MAX_LIMIT"),
                safety_notes=(
                    "Backfill plans are dry-run planning records.",
                    "Does not mutate source artifacts or execute trading workflows.",
                ),
                metadata={"heartbeatSupported": False},
            )
        )
    return definitions


def module_exists(module_name: str) -> bool:
    return find_spec(module_name) is not None


def available_if_module(module_name: str) -> RuntimeWorkerDefinitionStatus:
    if module_exists(module_name):
        return RuntimeWorkerDefinitionStatus.AVAILABLE
    return RuntimeWorkerDefinitionStatus.UNAVAILABLE


def enabled_module_status(module_name: str, enabled: bool) -> RuntimeWorkerDefinitionStatus:
    if not module_exists(module_name):
        return RuntimeWorkerDefinitionStatus.UNAVAILABLE
    if enabled:
        return RuntimeWorkerDefinitionStatus.AVAILABLE
    return RuntimeWorkerDefinitionStatus.DISABLED


def worker_component_enabled(settings: Settings, component: WorkerSupervisorComponent) -> bool:
    return component in settings.worker_supervisor_components
