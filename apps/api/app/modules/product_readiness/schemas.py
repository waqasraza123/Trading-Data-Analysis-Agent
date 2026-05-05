from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.product_readiness.models import (
    ProductReadinessCheckStatus,
    ProductReadinessLabel,
    ProductReadinessRunStatus,
)


class ProductReadinessRunRequest(ApiSchema):
    workspace_id: UUID | None = None


class ProductReadinessCheckRead(ApiSchema):
    key: str
    status: ProductReadinessCheckStatus
    title: str
    summary: str
    remediation: str
    related_route: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ProductReadinessRunRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    status: ProductReadinessRunStatus
    readiness_version: str
    readiness_score: float
    readiness_label: ProductReadinessLabel
    summary: str
    checks_json: list[ProductReadinessCheckRead]
    blockers_json: list[ProductReadinessCheckRead]
    warnings_json: list[ProductReadinessCheckRead]
    created_at: datetime
    updated_at: datetime


class ProductReadinessRunListResponse(ApiSchema):
    runs: list[ProductReadinessRunRead]
