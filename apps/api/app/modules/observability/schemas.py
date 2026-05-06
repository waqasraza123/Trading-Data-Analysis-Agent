from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema


class ObservabilityStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


class ObservabilityComponentRead(ApiSchema):
    name: str
    status: ObservabilityStatus
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class HttpMetricSummary(ApiSchema):
    request_count: int
    error_count: int
    error_rate: float
    duration_count: int
    duration_average_ms: float | None
    duration_max_ms: float | None
    warning_threshold_ms: int


class ObservabilityMetricsRead(ApiSchema):
    enabled: bool
    collected_at: datetime
    service: str
    metrics_format: str
    http: dict[str, Any]
    operations: dict[str, Any]
    summary: HttpMetricSummary


class ServiceSloRead(ApiSchema):
    status: ObservabilityStatus
    slo_version: str
    generated_at: datetime
    workspace_id: UUID | None = None
    components: list[ObservabilityComponentRead]
    summary: str
    metrics: dict[str, Any] = Field(default_factory=dict)


class ServiceSloSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    status: ObservabilityStatus
    slo_version: str
    snapshot_json: dict[str, Any]
    created_at: datetime


class TracingStatusRead(ApiSchema):
    enabled: bool
    provider_required_at_startup: bool
    mode: str
    hooks: list[str]
    service: str
    notes: list[str]
