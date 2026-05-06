from app.modules.observability.metrics import ServiceMetricsRegistry, normalize_metric_path
from app.modules.observability.schemas import ObservabilityComponentRead, ObservabilityStatus
from app.modules.observability.slo import (
    aggregate_component_status,
    data_freshness_component,
    provider_health_component,
    queue_health_component,
)


def test_aggregate_component_status_prioritizes_failing() -> None:
    components = [
        ObservabilityComponentRead(
            name="api_readiness",
            status=ObservabilityStatus.HEALTHY,
            summary="ok",
        ),
        ObservabilityComponentRead(
            name="provider_health",
            status=ObservabilityStatus.FAILING,
            summary="failed",
        ),
    ]

    assert aggregate_component_status(components) == ObservabilityStatus.FAILING


def test_aggregate_component_status_ignores_unknown_when_known_components_are_healthy() -> None:
    components = [
        ObservabilityComponentRead(
            name="api_readiness",
            status=ObservabilityStatus.HEALTHY,
            summary="ok",
        ),
        ObservabilityComponentRead(
            name="queue_health",
            status=ObservabilityStatus.UNKNOWN,
            summary="missing",
        ),
    ]

    assert aggregate_component_status(components) == ObservabilityStatus.HEALTHY


def test_provider_health_component_uses_configured_failure_threshold() -> None:
    metrics = {
        "provider_health_snapshots": {
            "available": True,
            "by_status": {"healthy": 2, "failing": 1},
        },
        "provider_polling_requests": {
            "available": True,
            "by_status": {"failed": 2},
        },
        "derived": {"providerFailureCount": 3},
    }

    component = provider_health_component(metrics, failure_warning_count=3)

    assert component.status == ObservabilityStatus.FAILING
    assert component.details["failureCount"] == 3


def test_data_freshness_component_flags_stale_market_memory() -> None:
    metrics = {
        "rolling_market_state_snapshots": {
            "available": True,
            "by_freshness_label": {"fresh": 4, "stale": 5},
        },
        "derived": {
            "staleMarketMemoryCount": 5,
            "highDataQualityFindingCount": 0,
        },
    }

    component = data_freshness_component(metrics, stale_warning_count=5)

    assert component.status == ObservabilityStatus.FAILING
    assert component.details["staleMarketMemoryCount"] == 5


def test_queue_health_is_unknown_when_job_queue_table_is_absent() -> None:
    component = queue_health_component({"job_queue_items": {"available": False}})

    assert component.status == ObservabilityStatus.UNKNOWN


def test_request_metrics_registry_records_http_summary() -> None:
    registry = ServiceMetricsRegistry()

    registry.record_request("get", "/workspaces/00000000-0000-0000-0000-000000000001", 200, 42.5)
    registry.record_request("get", "/workspaces/00000000-0000-0000-0000-000000000001", 500, 1500)

    summary = registry.http_summary(warning_threshold_ms=1000)

    assert summary.request_count == 2
    assert summary.error_count == 1
    assert summary.duration_max_ms == 1500
    assert normalize_metric_path("/workspaces/00000000-0000-0000-0000-000000000001") == (
        "/workspaces/{id}"
    )
