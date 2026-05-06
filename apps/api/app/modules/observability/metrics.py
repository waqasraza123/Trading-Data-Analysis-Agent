import re
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.observability.schemas import HttpMetricSummary, ObservabilityMetricsRead

REQUEST_DURATION_BUCKETS_MS = (50, 100, 250, 500, 1000, 2500, 5000)
IDENTIFIER_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
UUID_RE = re.compile(
    r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?=/|$)"
)
NUMBER_RE = re.compile(r"/[0-9]+(?=/|$)")


@dataclass
class RequestDurationStats:
    count: int = 0
    total_ms: float = 0.0
    min_ms: float | None = None
    max_ms: float | None = None
    buckets: dict[str, int] = field(
        default_factory=lambda: {str(bucket): 0 for bucket in REQUEST_DURATION_BUCKETS_MS}
    )

    def record(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = duration_ms if self.min_ms is None else min(self.min_ms, duration_ms)
        self.max_ms = duration_ms if self.max_ms is None else max(self.max_ms, duration_ms)
        for bucket in REQUEST_DURATION_BUCKETS_MS:
            if duration_ms <= bucket:
                self.buckets[str(bucket)] += 1

    def snapshot(self) -> dict[str, Any]:
        average_ms = self.total_ms / self.count if self.count else None
        return {
            "count": self.count,
            "totalMs": round(self.total_ms, 3),
            "averageMs": round(average_ms, 3) if average_ms is not None else None,
            "minMs": round(self.min_ms, 3) if self.min_ms is not None else None,
            "maxMs": round(self.max_ms, 3) if self.max_ms is not None else None,
            "bucketsMs": dict(self.buckets),
        }


class ServiceMetricsRegistry:
    def __init__(self) -> None:
        self.started_at = datetime.now(UTC)
        self._lock = threading.Lock()
        self._request_counts: dict[tuple[str, str, int], int] = {}
        self._request_durations: dict[tuple[str, str, int], RequestDurationStats] = {}

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        key = (method.upper(), normalize_metric_path(path), status_code)
        with self._lock:
            self._request_counts[key] = self._request_counts.get(key, 0) + 1
            stats = self._request_durations.setdefault(key, RequestDurationStats())
            stats.record(duration_ms)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            request_counts = [
                {
                    "method": method,
                    "path": path,
                    "statusCode": status_code,
                    "count": count,
                }
                for (method, path, status_code), count in sorted(self._request_counts.items())
            ]
            duration_summaries = [
                {
                    "method": method,
                    "path": path,
                    "statusCode": status_code,
                    **stats.snapshot(),
                }
                for (method, path, status_code), stats in sorted(
                    self._request_durations.items()
                )
            ]
        return {
            "startedAt": self.started_at.isoformat(),
            "requests": request_counts,
            "durations": duration_summaries,
        }

    def http_summary(self, warning_threshold_ms: int) -> HttpMetricSummary:
        snapshot = self.snapshot()
        requests = list_dict(snapshot.get("requests"))
        durations = list_dict(snapshot.get("durations"))
        request_count = sum(int(item.get("count", 0)) for item in requests)
        error_count = sum(
            int(item.get("count", 0))
            for item in requests
            if int(item.get("statusCode", 0)) >= 500
        )
        duration_count = sum(int(item.get("count", 0)) for item in durations)
        total_ms = sum(float(item.get("totalMs", 0.0)) for item in durations)
        max_values = [
            float(item["maxMs"])
            for item in durations
            if isinstance(item.get("maxMs"), int | float)
        ]
        average_ms = total_ms / duration_count if duration_count else None
        error_rate = error_count / request_count if request_count else 0.0
        return HttpMetricSummary(
            request_count=request_count,
            error_count=error_count,
            error_rate=round(error_rate, 6),
            duration_count=duration_count,
            duration_average_ms=round(average_ms, 3) if average_ms is not None else None,
            duration_max_ms=round(max(max_values), 3) if max_values else None,
            warning_threshold_ms=warning_threshold_ms,
        )


service_metrics_registry = ServiceMetricsRegistry()


class DatabaseMetricsCollector:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def collect(self, workspace_id: UUID | None = None) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        await self.add_grouped_table(metrics, "analysis_runs", ("status",), workspace_id)
        await self.add_grouped_table(
            metrics,
            "provider_polling_requests",
            ("status", "provider"),
            workspace_id,
        )
        await self.add_grouped_table(
            metrics,
            "provider_health_snapshots",
            ("status", "freshness_label", "provider"),
            workspace_id,
        )
        await self.add_grouped_table(
            metrics,
            "live_feed_subscriptions",
            ("status", "provider"),
            workspace_id,
        )
        await self.add_grouped_table(
            metrics,
            "rolling_market_state_snapshots",
            ("freshness_label", "data_quality_label"),
            workspace_id,
        )
        await self.add_grouped_table(
            metrics,
            "data_quality_findings",
            ("severity", "finding_type"),
            workspace_id,
        )
        await self.add_grouped_table(metrics, "runtime_worker_instances", ("status",), workspace_id)
        await self.add_grouped_table(
            metrics,
            "runtime_worker_run_requests",
            ("status", "worker_definition_key"),
            workspace_id,
        )
        await self.add_grouped_table(metrics, "notification_events", ("status",), workspace_id)
        await self.add_grouped_table(metrics, "notification_messages", ("status",), workspace_id)
        await self.add_grouped_table(metrics, "engine_execution_records", ("status",), workspace_id)
        await self.add_grouped_table(metrics, "scheduled_scan_runs", ("status",), workspace_id)
        await self.add_grouped_table(
            metrics,
            "job_queue_items",
            ("status", "queue_name", "job_type"),
            workspace_id,
        )
        metrics["derived"] = self.derived_metrics(metrics)
        return metrics

    async def add_grouped_table(
        self,
        metrics: dict[str, Any],
        table_name: str,
        group_columns: Sequence[str],
        workspace_id: UUID | None,
    ) -> None:
        columns = await self.table_columns(table_name)
        if columns is None:
            metrics[table_name] = {"available": False}
            return
        table_metrics: dict[str, Any] = {
            "available": True,
            "total": await self.count_rows(table_name, columns, workspace_id),
        }
        for column_name in group_columns:
            if column_name in columns:
                table_metrics[f"by_{column_name}"] = await self.count_grouped(
                    table_name,
                    column_name,
                    columns,
                    workspace_id,
                )
        metrics[table_name] = table_metrics

    async def table_columns(self, table_name: str) -> set[str] | None:
        validate_identifier(table_name)
        statement = text(
            "select column_name from information_schema.columns "
            "where table_schema = 'public' and table_name = :table_name"
        )
        result = await self.session.execute(statement, {"table_name": table_name})
        columns = {str(row[0]) for row in result.all()}
        return columns or None

    async def count_rows(
        self,
        table_name: str,
        columns: set[str],
        workspace_id: UUID | None,
    ) -> int:
        where_sql, params = build_workspace_filter(columns, workspace_id)
        result = await self.session.execute(
            text(f"select count(*) from {table_name}{where_sql}"),
            params,
        )
        return int(result.scalar_one())

    async def count_grouped(
        self,
        table_name: str,
        column_name: str,
        columns: set[str],
        workspace_id: UUID | None,
    ) -> dict[str, int]:
        validate_identifier(table_name)
        validate_identifier(column_name)
        where_sql, params = build_workspace_filter(columns, workspace_id)
        statement = text(
            f"select {column_name}, count(*) from {table_name}"
            f"{where_sql} group by {column_name} order by {column_name}"
        )
        result = await self.session.execute(statement, params)
        return {normalize_group_key(row[0]): int(row[1]) for row in result.all()}

    def derived_metrics(self, metrics: Mapping[str, Any]) -> dict[str, int]:
        provider_polling_failed = grouped_count(
            metrics,
            "provider_polling_requests",
            "by_status",
            "failed",
        )
        live_failed = grouped_count(metrics, "live_feed_subscriptions", "by_status", "failed")
        provider_failing = grouped_count(
            metrics,
            "provider_health_snapshots",
            "by_status",
            "failing",
        ) + grouped_count(metrics, "provider_health_snapshots", "by_status", "unavailable")
        stale_market_memory = sum(
            grouped_count(metrics, "rolling_market_state_snapshots", "by_freshness_label", value)
            for value in ("stale", "delayed", "no_data")
        )
        high_quality_findings = grouped_count(
            metrics,
            "data_quality_findings",
            "by_severity",
            "high",
        )
        failed_backend_operations = sum(
            grouped_count(metrics, table, "by_status", "failed")
            for table in (
                "analysis_runs",
                "provider_polling_requests",
                "runtime_worker_run_requests",
                "notification_events",
                "notification_messages",
                "engine_execution_records",
                "scheduled_scan_runs",
                "job_queue_items",
            )
        )
        return {
            "providerFailureCount": provider_polling_failed + live_failed + provider_failing,
            "staleMarketMemoryCount": stale_market_memory,
            "highDataQualityFindingCount": high_quality_findings,
            "failedBackendOperationCount": failed_backend_operations,
            "queueDepth": sum(
                grouped_count(metrics, "job_queue_items", "by_status", value)
                for value in ("pending", "scheduled", "retrying", "running")
            ),
        }


async def collect_observability_metrics(
    settings: Settings,
    session: AsyncSession | None = None,
    workspace_id: UUID | None = None,
) -> ObservabilityMetricsRead:
    http_metrics = service_metrics_registry.snapshot()
    database_metrics: dict[str, Any] = {}
    if session is not None:
        database_metrics = await DatabaseMetricsCollector(session).collect(workspace_id)
    operations = {"database": database_metrics}
    return ObservabilityMetricsRead(
        enabled=settings.observability_enabled,
        collected_at=datetime.now(UTC),
        service=settings.service_name,
        metrics_format="json",
        http=http_metrics,
        operations=operations,
        summary=service_metrics_registry.http_summary(settings.request_latency_warning_ms),
    )


def observability_metrics_to_prometheus(metrics: ObservabilityMetricsRead) -> str:
    lines = [
        "# HELP service_http_requests_total HTTP requests recorded by the API process.",
        "# TYPE service_http_requests_total counter",
    ]
    for item in list_dict(metrics.http.get("requests")):
        labels = prometheus_labels(
            {
                "method": str(item.get("method", "")),
                "path": str(item.get("path", "")),
                "status": str(item.get("statusCode", "")),
            }
        )
        lines.append(f"service_http_requests_total{labels} {int(item.get('count', 0))}")
    lines.extend(
        [
            "# HELP service_http_request_duration_ms Request duration summary in milliseconds.",
            "# TYPE service_http_request_duration_ms summary",
        ]
    )
    for item in list_dict(metrics.http.get("durations")):
        base_labels = {
            "method": str(item.get("method", "")),
            "path": str(item.get("path", "")),
            "status": str(item.get("statusCode", "")),
        }
        labels = prometheus_labels(base_labels)
        lines.append(f"service_http_request_duration_ms_count{labels} {int(item.get('count', 0))}")
        lines.append(
            f"service_http_request_duration_ms_sum{labels} {float(item.get('totalMs', 0.0))}"
        )
        for bucket, count in dict_str_int(item.get("bucketsMs")).items():
            bucket_labels = prometheus_labels({**base_labels, "le": bucket})
            lines.append(f"service_http_request_duration_ms_bucket{bucket_labels} {count}")
        inf_labels = prometheus_labels({**base_labels, "le": "+Inf"})
        lines.append(f"service_http_request_duration_ms_bucket{inf_labels} {item.get('count', 0)}")
    database_metrics = dict_any(metrics.operations.get("database"))
    derived = dict_any(database_metrics.get("derived"))
    lines.extend(
        [
            "# HELP service_backend_operations_failed_total Failed backend operation count.",
            "# TYPE service_backend_operations_failed_total gauge",
            "service_backend_operations_failed_total "
            f"{int(derived.get('failedBackendOperationCount', 0))}",
            "# HELP service_provider_failures_total Provider failure count.",
            "# TYPE service_provider_failures_total gauge",
            f"service_provider_failures_total {int(derived.get('providerFailureCount', 0))}",
            "# HELP service_stale_market_memory_total Stale market memory count.",
            "# TYPE service_stale_market_memory_total gauge",
            f"service_stale_market_memory_total {int(derived.get('staleMarketMemoryCount', 0))}",
            "# HELP service_job_queue_depth Job queue depth when queue tables exist.",
            "# TYPE service_job_queue_depth gauge",
            f"service_job_queue_depth {int(derived.get('queueDepth', 0))}",
        ]
    )
    append_grouped_gauges(lines, database_metrics)
    return "\n".join(lines) + "\n"


def append_grouped_gauges(lines: list[str], database_metrics: Mapping[str, Any]) -> None:
    for table_name, table_metrics in sorted(database_metrics.items()):
        if table_name == "derived":
            continue
        table_payload = dict_any(table_metrics)
        if not table_payload.get("available"):
            continue
        metric_name = f"service_{sanitize_metric_name(table_name)}_total"
        lines.append(f"# TYPE {metric_name} gauge")
        lines.append(f"{metric_name} {int(table_payload.get('total', 0))}")
        for key, value in table_payload.items():
            if not key.startswith("by_"):
                continue
            label_name = key.removeprefix("by_")
            grouped_values = dict_str_int(value)
            for label_value, count in grouped_values.items():
                labels = prometheus_labels({label_name: label_value})
                lines.append(f"{metric_name}{labels} {count}")


def normalize_metric_path(path: str) -> str:
    normalized = UUID_RE.sub("/{id}", path)
    return NUMBER_RE.sub("/{id}", normalized)


def build_workspace_filter(
    columns: set[str],
    workspace_id: UUID | None,
) -> tuple[str, dict[str, Any]]:
    if workspace_id is None or "workspace_id" not in columns:
        return "", {}
    return " where workspace_id = :workspace_id", {"workspace_id": workspace_id}


def grouped_count(
    metrics: Mapping[str, Any],
    table_name: str,
    group_name: str,
    value: str,
) -> int:
    table_metrics = dict_any(metrics.get(table_name))
    grouped_values = dict_str_int(table_metrics.get(group_name))
    return grouped_values.get(value, 0)


def normalize_group_key(value: object) -> str:
    if value is None:
        return "null"
    return str(value)


def validate_identifier(value: str) -> None:
    if IDENTIFIER_RE.fullmatch(value) is None:
        msg = f"Unsafe SQL identifier: {value}"
        raise ValueError(msg)


def prometheus_labels(labels: Mapping[str, str]) -> str:
    if not labels:
        return ""
    rendered = ",".join(
        f'{sanitize_metric_name(key)}="{escape_prometheus_label(value)}"'
        for key, value in sorted(labels.items())
    )
    return f"{{{rendered}}}"


def sanitize_metric_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def escape_prometheus_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def dict_any(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def dict_str_int(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): int(raw_value)
        for key, raw_value in value.items()
        if isinstance(raw_value, int)
    }


def list_dict(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
