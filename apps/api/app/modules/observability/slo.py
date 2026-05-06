from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.session import check_database_connection
from app.modules.observability.metrics import (
    DatabaseMetricsCollector,
    dict_any,
    grouped_count,
    service_metrics_registry,
)
from app.modules.observability.models import ServiceSloSnapshot
from app.modules.observability.schemas import (
    ObservabilityComponentRead,
    ObservabilityStatus,
    ServiceSloRead,
)


async def calculate_service_slo(
    settings: Settings,
    session: AsyncSession | None = None,
    workspace_id: UUID | None = None,
) -> ServiceSloRead:
    generated_at = datetime.now(UTC)
    database_status, database_summary = await database_component_status(settings)
    database_metrics: dict[str, object] = {}
    if session is not None:
        database_metrics = await DatabaseMetricsCollector(session).collect(workspace_id)
    components = [
        ObservabilityComponentRead(
            name="api_readiness",
            status=ObservabilityStatus.HEALTHY
            if settings.observability_enabled
            else ObservabilityStatus.UNKNOWN,
            summary="API process is serving observability requests."
            if settings.observability_enabled
            else "Observability is disabled.",
            details={"observabilityEnabled": settings.observability_enabled},
        ),
        ObservabilityComponentRead(
            name="db_health",
            status=database_status,
            summary=database_summary,
            details={"databaseConfigured": settings.database_url is not None},
        ),
        worker_health_component(database_metrics, settings.worker_stale_warning_seconds),
        provider_health_component(database_metrics, settings.provider_failure_warning_count),
        data_freshness_component(database_metrics, settings.stale_data_warning_count),
        queue_health_component(database_metrics),
        error_rate_component(),
        latency_component(settings.request_latency_warning_ms),
    ]
    status = aggregate_component_status(components)
    return ServiceSloRead(
        status=status,
        slo_version=settings.slo_version,
        generated_at=generated_at,
        workspace_id=workspace_id,
        components=components,
        summary=slo_summary(status),
        metrics={
            "http": service_metrics_registry.http_summary(
                settings.request_latency_warning_ms
            ).model_dump(by_alias=True),
            "database": database_metrics,
        },
    )


async def persist_service_slo_snapshot(
    session: AsyncSession,
    slo: ServiceSloRead,
) -> ServiceSloSnapshot:
    snapshot = ServiceSloSnapshot(
        workspace_id=slo.workspace_id,
        status=slo.status.value,
        slo_version=slo.slo_version,
        snapshot_json=slo.model_dump(mode="json", by_alias=True),
    )
    session.add(snapshot)
    await session.flush()
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


async def database_component_status(settings: Settings) -> tuple[ObservabilityStatus, str]:
    if settings.database_url is None:
        return ObservabilityStatus.UNKNOWN, "DATABASE_URL is not configured."
    database_is_healthy, message = await check_database_connection(settings)
    if database_is_healthy:
        return ObservabilityStatus.HEALTHY, "Database connectivity check succeeded."
    return ObservabilityStatus.FAILING, message


def worker_health_component(
    metrics: Mapping[str, object],
    stale_warning_seconds: int,
) -> ObservabilityComponentRead:
    worker_instances = dict_any(metrics.get("runtime_worker_instances"))
    if not worker_instances.get("available"):
        return component_unknown("worker_health", "Runtime worker tables are not available.")
    status_counts = dict_any(worker_instances.get("by_status"))
    failed_count = int(status_counts.get("failed", 0))
    stale_count = int(status_counts.get("stale", 0))
    running_count = int(status_counts.get("running", 0))
    if failed_count:
        status = ObservabilityStatus.FAILING
        summary = "Runtime worker failures are present."
    elif stale_count:
        status = ObservabilityStatus.DEGRADED
        summary = "Runtime worker heartbeats are stale."
    else:
        status = ObservabilityStatus.HEALTHY
        summary = "Runtime worker health has no failing or stale instances."
    return ObservabilityComponentRead(
        name="worker_health",
        status=status,
        summary=summary,
        details={
            "runningCount": running_count,
            "staleCount": stale_count,
            "failedCount": failed_count,
            "staleWarningSeconds": stale_warning_seconds,
        },
    )


def provider_health_component(
    metrics: Mapping[str, object],
    failure_warning_count: int,
) -> ObservabilityComponentRead:
    provider_health = dict_any(metrics.get("provider_health_snapshots"))
    provider_polling = dict_any(metrics.get("provider_polling_requests"))
    if not provider_health.get("available") and not provider_polling.get("available"):
        return component_unknown("provider_health", "Provider health tables are not available.")
    derived = dict_any(metrics.get("derived"))
    failure_count = int(derived.get("providerFailureCount", 0))
    degraded_count = grouped_count(metrics, "provider_health_snapshots", "by_status", "degraded")
    stale_count = grouped_count(metrics, "provider_health_snapshots", "by_status", "stale")
    if failure_count >= failure_warning_count:
        status = ObservabilityStatus.FAILING
        summary = "Provider failure count exceeds the configured warning threshold."
    elif failure_count or degraded_count or stale_count:
        status = ObservabilityStatus.DEGRADED
        summary = "Provider health has failures, degraded snapshots, or stale snapshots."
    else:
        status = ObservabilityStatus.HEALTHY
        summary = "Provider health has no current failure counters."
    return ObservabilityComponentRead(
        name="provider_health",
        status=status,
        summary=summary,
        details={
            "failureCount": failure_count,
            "degradedCount": degraded_count,
            "staleCount": stale_count,
            "failureWarningCount": failure_warning_count,
        },
    )


def data_freshness_component(
    metrics: Mapping[str, object],
    stale_warning_count: int,
) -> ObservabilityComponentRead:
    market_memory = dict_any(metrics.get("rolling_market_state_snapshots"))
    if not market_memory.get("available"):
        return component_unknown("data_freshness", "Market memory tables are not available.")
    derived = dict_any(metrics.get("derived"))
    stale_count = int(derived.get("staleMarketMemoryCount", 0))
    high_findings = int(derived.get("highDataQualityFindingCount", 0))
    if stale_count >= stale_warning_count:
        status = ObservabilityStatus.FAILING
        summary = "Stale market memory exceeds the configured warning threshold."
    elif stale_count or high_findings:
        status = ObservabilityStatus.DEGRADED
        summary = "Data freshness or quality counters need operator review."
    else:
        status = ObservabilityStatus.HEALTHY
        summary = "Data freshness counters are within configured thresholds."
    return ObservabilityComponentRead(
        name="data_freshness",
        status=status,
        summary=summary,
        details={
            "staleMarketMemoryCount": stale_count,
            "highDataQualityFindingCount": high_findings,
            "staleDataWarningCount": stale_warning_count,
        },
    )


def queue_health_component(metrics: Mapping[str, object]) -> ObservabilityComponentRead:
    queue_metrics = dict_any(metrics.get("job_queue_items"))
    if not queue_metrics.get("available"):
        return component_unknown("queue_health", "Job queue table is not available.")
    failed_count = grouped_count(metrics, "job_queue_items", "by_status", "failed")
    dead_letter_count = grouped_count(metrics, "job_queue_items", "by_status", "dead_letter")
    retrying_count = grouped_count(metrics, "job_queue_items", "by_status", "retrying")
    queue_depth = int(dict_any(metrics.get("derived")).get("queueDepth", 0))
    if dead_letter_count or failed_count:
        status = ObservabilityStatus.FAILING
        summary = "Job queue has failed or dead-lettered items."
    elif retrying_count:
        status = ObservabilityStatus.DEGRADED
        summary = "Job queue has retrying items."
    else:
        status = ObservabilityStatus.HEALTHY
        summary = "Job queue has no failed or dead-lettered items."
    return ObservabilityComponentRead(
        name="queue_health",
        status=status,
        summary=summary,
        details={
            "queueDepth": queue_depth,
            "failedCount": failed_count,
            "retryingCount": retrying_count,
            "deadLetterCount": dead_letter_count,
        },
    )


def error_rate_component() -> ObservabilityComponentRead:
    summary = service_metrics_registry.http_summary(warning_threshold_ms=0)
    if summary.request_count == 0:
        return component_unknown("error_rate", "No HTTP requests have been recorded yet.")
    if summary.error_rate >= 0.10:
        status = ObservabilityStatus.FAILING
        component_summary = "HTTP 5xx error rate is at or above 10%."
    elif summary.error_rate >= 0.02:
        status = ObservabilityStatus.DEGRADED
        component_summary = "HTTP 5xx error rate is at or above 2%."
    else:
        status = ObservabilityStatus.HEALTHY
        component_summary = "HTTP 5xx error rate is below warning thresholds."
    return ObservabilityComponentRead(
        name="error_rate",
        status=status,
        summary=component_summary,
        details={
            "requestCount": summary.request_count,
            "errorCount": summary.error_count,
            "errorRate": summary.error_rate,
        },
    )


def latency_component(warning_threshold_ms: int) -> ObservabilityComponentRead:
    summary = service_metrics_registry.http_summary(warning_threshold_ms)
    if summary.duration_count == 0:
        return component_unknown("latency_status", "No HTTP durations have been recorded yet.")
    max_ms = summary.duration_max_ms or 0.0
    average_ms = summary.duration_average_ms or 0.0
    if max_ms >= warning_threshold_ms * 2:
        status = ObservabilityStatus.FAILING
        component_summary = "Maximum request latency is above the failing threshold."
    elif average_ms >= warning_threshold_ms or max_ms >= warning_threshold_ms:
        status = ObservabilityStatus.DEGRADED
        component_summary = "Request latency exceeded the configured warning threshold."
    else:
        status = ObservabilityStatus.HEALTHY
        component_summary = "Request latency is within configured thresholds."
    return ObservabilityComponentRead(
        name="latency_status",
        status=status,
        summary=component_summary,
        details={
            "durationAverageMs": average_ms,
            "durationMaxMs": max_ms,
            "warningThresholdMs": warning_threshold_ms,
        },
    )


def aggregate_component_status(
    components: list[ObservabilityComponentRead],
) -> ObservabilityStatus:
    statuses = [component.status for component in components]
    if ObservabilityStatus.FAILING in statuses:
        return ObservabilityStatus.FAILING
    if ObservabilityStatus.DEGRADED in statuses:
        return ObservabilityStatus.DEGRADED
    known_statuses = [status for status in statuses if status != ObservabilityStatus.UNKNOWN]
    if not known_statuses:
        return ObservabilityStatus.UNKNOWN
    return ObservabilityStatus.HEALTHY


def component_unknown(name: str, summary: str) -> ObservabilityComponentRead:
    return ObservabilityComponentRead(
        name=name,
        status=ObservabilityStatus.UNKNOWN,
        summary=summary,
        details={},
    )


def slo_summary(status: ObservabilityStatus) -> str:
    if status == ObservabilityStatus.HEALTHY:
        return "Service SLO components are healthy."
    if status == ObservabilityStatus.DEGRADED:
        return "One or more service SLO components are degraded."
    if status == ObservabilityStatus.FAILING:
        return "One or more service SLO components are failing."
    return "Service SLO status is unknown because there is not enough operational signal."
