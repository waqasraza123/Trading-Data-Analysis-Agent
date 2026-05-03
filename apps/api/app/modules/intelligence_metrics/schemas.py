from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.intelligence_metrics.models import (
    IntelligenceMetricSnapshotStatus,
    IntelligenceMetricSnapshotType,
)


class IntelligenceMetricWarning(ApiSchema):
    module_name: str
    table_name: str | None = None
    column_name: str | None = None
    code: str
    message: str


class IntelligenceMetricsRead(ApiSchema):
    workspace_id: UUID | None = None
    module_name: str | None = None
    snapshot_type: IntelligenceMetricSnapshotType
    status: IntelligenceMetricSnapshotStatus
    collected_at: datetime
    metrics_json: dict[str, Any]
    warnings_json: list[IntelligenceMetricWarning]
    health_summary: dict[str, Any]


class IntelligenceMetricSnapshotRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    snapshot_type: IntelligenceMetricSnapshotType
    status: IntelligenceMetricSnapshotStatus
    collected_at: datetime
    metrics_json: dict[str, Any]
    warnings_json: list[dict[str, Any]]
    created_at: datetime


class IntelligenceMetricSnapshotListQuery(ApiSchema):
    workspace_id: UUID | None = None
    snapshot_type: IntelligenceMetricSnapshotType | None = None
    status: IntelligenceMetricSnapshotStatus | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_global_workspace_filter(self) -> "IntelligenceMetricSnapshotListQuery":
        if (
            self.workspace_id is not None
            and self.snapshot_type == IntelligenceMetricSnapshotType.GLOBAL
        ):
            msg = "workspace_id cannot be combined with global snapshot_type"
            raise ValueError(msg)
        return self
