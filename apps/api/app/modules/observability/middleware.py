import logging

from fastapi import Request

from app.config import Settings
from app.modules.observability.metrics import normalize_metric_path, service_metrics_registry


def record_observed_request(
    request: Request,
    settings: Settings,
    status_code: int,
    duration_ms: float,
) -> None:
    if not settings.observability_enabled:
        return
    path = observed_route_path(request)
    service_metrics_registry.record_request(
        method=request.method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
    )
    if duration_ms >= settings.request_latency_warning_ms:
        logging.getLogger(settings.service_name).warning(
            "request_latency_warning",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": normalize_metric_path(path),
                "status_code": status_code,
                "duration_ms": round(duration_ms, 3),
                "warning_threshold_ms": settings.request_latency_warning_ms,
            },
        )


def observed_route_path(request: Request) -> str:
    route = request.scope.get("route")
    route_path = getattr(route, "path", None)
    if isinstance(route_path, str) and route_path:
        return route_path
    return request.url.path
