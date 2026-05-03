from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.modules.intelligence_metrics.models import (
    IntelligenceMetricSnapshotStatus,
    IntelligenceMetricSnapshotType,
)
from app.modules.intelligence_metrics.repository import IntelligenceMetricsRepository, utc_now


@dataclass(frozen=True)
class MetricTableDefinition:
    module_name: str
    table_name: str
    group_columns: tuple[str, ...] = ()
    required: bool = True


@dataclass
class CollectedMetrics:
    snapshot_type: IntelligenceMetricSnapshotType
    collected_at: datetime
    metrics_json: dict[str, object]
    warnings_json: list[dict[str, object]] = field(default_factory=list)

    @property
    def status(self) -> IntelligenceMetricSnapshotStatus:
        if self.warnings_json:
            return IntelligenceMetricSnapshotStatus.COMPLETED_WITH_WARNINGS
        return IntelligenceMetricSnapshotStatus.COMPLETED


class IntelligenceMetricCollector:
    def __init__(self, repository: IntelligenceMetricsRepository) -> None:
        self.repository = repository

    async def collect_workspace_metrics(self, workspace_id: UUID) -> CollectedMetrics:
        return await self.collect(
            snapshot_type=IntelligenceMetricSnapshotType.WORKSPACE,
            workspace_id=workspace_id,
        )

    async def collect_global_metrics(self) -> CollectedMetrics:
        return await self.collect(snapshot_type=IntelligenceMetricSnapshotType.GLOBAL)

    async def collect_module_metrics(
        self,
        module_name: str,
        workspace_id: UUID | None = None,
    ) -> CollectedMetrics:
        normalized_module_name = module_name.strip().lower()
        definitions = [
            definition
            for definition in metric_definitions()
            if definition.module_name == normalized_module_name
        ]
        collected_at = utc_now()
        warnings: list[dict[str, object]] = []
        if not definitions:
            warnings.append(
                warning(
                    module_name=normalized_module_name,
                    code="unknown_metrics_module",
                    message="Metrics module is not registered",
                )
            )
        modules = await self.collect_definitions(definitions, workspace_id, warnings)
        metrics_json = build_metrics_payload(
            snapshot_type=IntelligenceMetricSnapshotType.MODULE,
            collected_at=collected_at,
            workspace_id=workspace_id,
            module_name=normalized_module_name,
            modules=modules,
            warnings=warnings,
        )
        return CollectedMetrics(
            snapshot_type=IntelligenceMetricSnapshotType.MODULE,
            collected_at=collected_at,
            metrics_json=metrics_json,
            warnings_json=warnings,
        )

    async def collect(
        self,
        snapshot_type: IntelligenceMetricSnapshotType,
        workspace_id: UUID | None = None,
    ) -> CollectedMetrics:
        collected_at = utc_now()
        warnings: list[dict[str, object]] = []
        modules = await self.collect_definitions(metric_definitions(), workspace_id, warnings)
        metrics_json = build_metrics_payload(
            snapshot_type=snapshot_type,
            collected_at=collected_at,
            workspace_id=workspace_id,
            module_name=None,
            modules=modules,
            warnings=warnings,
        )
        return CollectedMetrics(
            snapshot_type=snapshot_type,
            collected_at=collected_at,
            metrics_json=metrics_json,
            warnings_json=warnings,
        )

    async def collect_definitions(
        self,
        definitions: Sequence[MetricTableDefinition],
        workspace_id: UUID | None,
        warnings: list[dict[str, object]],
    ) -> dict[str, dict[str, object]]:
        modules: dict[str, dict[str, object]] = {}
        for definition in definitions:
            table_metrics = await self.collect_table(definition, workspace_id, warnings)
            if table_metrics is None:
                continue
            module_metrics = modules.setdefault(definition.module_name, {})
            module_metrics[definition.table_name] = table_metrics
        await self.add_derived_counts(modules, workspace_id, warnings)
        return modules

    async def collect_table(
        self,
        definition: MetricTableDefinition,
        workspace_id: UUID | None,
        warnings: list[dict[str, object]],
    ) -> dict[str, object] | None:
        columns = await self.repository.table_columns(definition.table_name)
        if columns is None:
            warnings.append(
                warning(
                    module_name=definition.module_name,
                    table_name=definition.table_name,
                    code="metrics_table_missing",
                    message="Metrics source table is not available",
                )
            )
            return None
        table_metrics: dict[str, object] = {
            "total": await self.repository.count_rows(
                definition.table_name,
                columns,
                workspace_id,
            )
        }
        for column_name in definition.group_columns:
            if column_name not in columns:
                warnings.append(
                    warning(
                        module_name=definition.module_name,
                        table_name=definition.table_name,
                        column_name=column_name,
                        code="metrics_column_missing",
                        message="Metrics source column is not available",
                    )
                )
                continue
            table_metrics[f"by_{column_name}"] = await self.repository.count_grouped(
                definition.table_name,
                column_name,
                columns,
                workspace_id,
            )
        return table_metrics

    async def add_derived_counts(
        self,
        modules: dict[str, dict[str, object]],
        workspace_id: UUID | None,
        warnings: list[dict[str, object]],
    ) -> None:
        now = datetime.now(UTC)
        action_columns = await self.repository.table_columns("reasoning_action_items")
        if action_columns is not None and {"status", "due_at"}.issubset(action_columns):
            action_metrics = modules.setdefault("action_plans", {}).setdefault(
                "reasoning_action_items",
                {},
            )
            if isinstance(action_metrics, dict):
                action_metrics["due_now"] = await self.repository.count_where(
                    "reasoning_action_items",
                    action_columns,
                    ["status in ('pending', 'due')", "due_at is not null", "due_at <= :now"],
                    workspace_id,
                    {"now": now},
                )

        chart_columns = await self.repository.table_columns("chart_screenshot_runs")
        if chart_columns is not None and "status" in chart_columns:
            chart_metrics = modules.setdefault("chart_screenshots", {}).setdefault(
                "chart_screenshot_runs",
                {},
            )
            if isinstance(chart_metrics, dict):
                chart_metrics["requires_review"] = await self.repository.count_where(
                    "chart_screenshot_runs",
                    chart_columns,
                    ["status = 'review_required'"],
                    workspace_id,
                )

        import_columns = await self.repository.table_columns("import_batches")
        if import_columns is not None and "rows_invalid" in import_columns:
            import_metrics = modules.setdefault("datasets", {}).setdefault("import_batches", {})
            if isinstance(import_metrics, dict):
                import_metrics["invalid_rows"] = await self.repository.count_where(
                    "import_batches",
                    import_columns,
                    ["rows_invalid > 0"],
                    workspace_id,
                )


def metric_definitions() -> list[MetricTableDefinition]:
    return [
        MetricTableDefinition("analysis", "analysis_runs", ("status", "analysis_mode")),
        MetricTableDefinition("signals", "signals", ("classification_status", "bias")),
        MetricTableDefinition(
            "outcomes",
            "signal_outcomes",
            ("outcome_label", "evaluation_status", "classification_status", "bias"),
        ),
        MetricTableDefinition(
            "reasoning",
            "llm_reasoning_runs",
            ("status", "safety_status", "grounding_status", "reasoning_type"),
        ),
        MetricTableDefinition(
            "action_plans",
            "reasoning_action_items",
            ("status", "action_type", "priority"),
        ),
        MetricTableDefinition(
            "market_scans",
            "market_scan_runs",
            ("status", "scan_type"),
            required=False,
        ),
        MetricTableDefinition(
            "profile_diagnostics",
            "strategy_profile_diagnostic_runs",
            ("status", "scope_type"),
        ),
        MetricTableDefinition(
            "profile_diagnostics",
            "strategy_profile_diagnostics",
            ("diagnostic_label",),
        ),
        MetricTableDefinition(
            "profile_diagnostics",
            "pattern_outcome_diagnostics",
            ("diagnostic_label",),
        ),
        MetricTableDefinition(
            "profile_diagnostics",
            "calibration_recommendations",
            ("severity", "status", "recommendation_type"),
        ),
        MetricTableDefinition(
            "quality",
            "data_quality_findings",
            ("severity", "status", "finding_type"),
            required=False,
        ),
        MetricTableDefinition("quality", "import_batches", ("status",)),
        MetricTableDefinition("quality", "import_errors", ("error_code",)),
        MetricTableDefinition(
            "operator_reviews",
            "operator_reviews",
            ("status", "review_type"),
            required=False,
        ),
        MetricTableDefinition(
            "chart_screenshots",
            "chart_screenshot_runs",
            ("status", "analysis_hypothesis"),
        ),
        MetricTableDefinition(
            "provider_polling",
            "provider_polling_requests",
            ("status", "provider"),
            required=False,
        ),
        MetricTableDefinition(
            "provider_polling",
            "live_feed_events",
            ("processing_status", "event_type", "provider"),
        ),
        MetricTableDefinition(
            "webhook_outbox",
            "webhook_outbox_events",
            ("status", "event_type"),
            required=False,
        ),
        MetricTableDefinition(
            "webhook_outbox",
            "webhook_outbox",
            ("status", "event_type"),
            required=False,
        ),
        MetricTableDefinition(
            "webhook_outbox",
            "notification_messages",
            ("status", "channel", "event_type", "severity"),
        ),
        MetricTableDefinition(
            "webhook_outbox",
            "notification_worker_runs",
            ("status",),
        ),
        MetricTableDefinition(
            "reports",
            "ai_intelligence_runs",
            ("status", "safety_status", "grounding_status", "subject_type"),
        ),
    ]


def build_metrics_payload(
    snapshot_type: IntelligenceMetricSnapshotType,
    collected_at: datetime,
    workspace_id: UUID | None,
    module_name: str | None,
    modules: dict[str, dict[str, object]],
    warnings: list[dict[str, object]],
) -> dict[str, object]:
    health_summary = build_health_summary(modules, warnings)
    return {
        "scope": {
            "snapshotType": snapshot_type.value,
            "workspaceId": str(workspace_id) if workspace_id is not None else None,
            "moduleName": module_name,
        },
        "collectedAt": collected_at.isoformat(),
        "modules": modules,
        "operationalHealth": health_summary,
    }


def build_health_summary(
    modules: dict[str, dict[str, object]],
    warnings: list[dict[str, object]],
) -> dict[str, object]:
    counters = {
        "failedAnalyses": grouped_count(modules, "analysis", "analysis_runs", "by_status", "failed"),
        "failedReasoningRuns": grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_status",
            "failed",
        ),
        "blockedReasoningRuns": grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_status",
            "blocked",
        )
        + grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_safety_status",
            "blocked",
        ),
        "fallbackReasoningRuns": grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_status",
            "fallback_used",
        )
        + grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_safety_status",
            "fallback_used",
        ),
        "ungroundedReasoningRuns": grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_grounding_status",
            "failed",
        )
        + grouped_count(
            modules,
            "reasoning",
            "llm_reasoning_runs",
            "by_grounding_status",
            "questionable",
        ),
        "dueActionItems": derived_count(
            modules,
            "action_plans",
            "reasoning_action_items",
            "due_now",
        )
        + grouped_count(
            modules,
            "action_plans",
            "reasoning_action_items",
            "by_status",
            "due",
        ),
        "failedActionItems": grouped_count(
            modules,
            "action_plans",
            "reasoning_action_items",
            "by_status",
            "failed",
        ),
        "reviewRequiredChartRuns": derived_count(
            modules,
            "chart_screenshots",
            "chart_screenshot_runs",
            "requires_review",
        ),
        "providerPollingFailures": grouped_count(
            modules,
            "provider_polling",
            "provider_polling_requests",
            "by_status",
            "failed",
        )
        + grouped_count(
            modules,
            "provider_polling",
            "live_feed_events",
            "by_processing_status",
            "failed",
        )
        + grouped_count(
            modules,
            "provider_polling",
            "live_feed_events",
            "by_event_type",
            "error",
        ),
        "outboxFailures": grouped_count(
            modules,
            "webhook_outbox",
            "webhook_outbox_events",
            "by_status",
            "failed",
        )
        + grouped_count(
            modules,
            "webhook_outbox",
            "webhook_outbox",
            "by_status",
            "failed",
        )
        + grouped_count(
            modules,
            "webhook_outbox",
            "notification_messages",
            "by_status",
            "failed",
        ),
        "dataQualityErrors": grouped_total(modules, "quality", "import_errors"),
        "missingModuleWarnings": len(
            [item for item in warnings if item.get("code") == "metrics_table_missing"]
        ),
    }
    failure_total = sum(
        counters[key]
        for key in (
            "failedAnalyses",
            "failedReasoningRuns",
            "failedActionItems",
            "providerPollingFailures",
            "outboxFailures",
        )
    )
    attention_total = sum(
        counters[key]
        for key in (
            "blockedReasoningRuns",
            "fallbackReasoningRuns",
            "ungroundedReasoningRuns",
            "dueActionItems",
            "reviewRequiredChartRuns",
            "dataQualityErrors",
        )
    )
    if failure_total > 0:
        status = "degraded"
    elif attention_total > 0:
        status = "attention"
    elif warnings:
        status = "partial"
    else:
        status = "healthy"
    return {
        "status": status,
        "counters": counters,
        "warningCount": len(warnings),
        "summary": build_health_sentence(status, counters),
    }


def grouped_count(
    modules: dict[str, dict[str, object]],
    module_name: str,
    table_name: str,
    group_name: str,
    value: str,
) -> int:
    table_metrics = modules.get(module_name, {}).get(table_name)
    if not isinstance(table_metrics, dict):
        return 0
    grouped_values = table_metrics.get(group_name)
    if not isinstance(grouped_values, dict):
        return 0
    count = grouped_values.get(value, 0)
    return int(count) if isinstance(count, int) else 0


def grouped_total(
    modules: dict[str, dict[str, object]],
    module_name: str,
    table_name: str,
) -> int:
    table_metrics = modules.get(module_name, {}).get(table_name)
    if not isinstance(table_metrics, dict):
        return 0
    total = table_metrics.get("total", 0)
    return int(total) if isinstance(total, int) else 0


def derived_count(
    modules: dict[str, dict[str, object]],
    module_name: str,
    table_name: str,
    field_name: str,
) -> int:
    table_metrics = modules.get(module_name, {}).get(table_name)
    if not isinstance(table_metrics, dict):
        return 0
    count = table_metrics.get(field_name, 0)
    return int(count) if isinstance(count, int) else 0


def build_health_sentence(status: str, counters: dict[str, int]) -> str:
    if status == "healthy":
        return "Backend intelligence counters show no current operational attention items."
    if status == "partial":
        return "Backend intelligence counters were collected with missing optional modules."
    if status == "attention":
        return "Backend intelligence counters show review, due-work, quality, or reasoning attention items."
    return "Backend intelligence counters show failed operational work that needs investigation."


def warning(
    module_name: str,
    code: str,
    message: str,
    table_name: str | None = None,
    column_name: str | None = None,
) -> dict[str, object]:
    return {
        "moduleName": module_name,
        "tableName": table_name,
        "columnName": column_name,
        "code": code,
        "message": message,
    }
