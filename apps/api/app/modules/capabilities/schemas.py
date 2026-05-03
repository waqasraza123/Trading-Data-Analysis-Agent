from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.capabilities.models import (
    CapabilityCategory,
    CapabilityExecutionType,
    CapabilitySafetyLevel,
    CapabilityStatus,
)


class CapabilityRuntimeAvailability(ApiSchema):
    installed: bool
    enabled: bool
    database_configured: bool
    external_credentials_configured: bool | None
    runtime_status: CapabilityStatus
    reasons: list[str]


class CapabilityRead(ApiReadSchema):
    id: UUID
    key: str
    name: str
    version: str
    category: CapabilityCategory
    status: CapabilityStatus
    execution_type: CapabilityExecutionType
    safety_level: CapabilitySafetyLevel
    requires_external_credentials: bool
    requires_database: bool
    input_contracts_json: list[dict[str, Any]]
    output_contracts_json: list[dict[str, Any]]
    produced_artifacts_json: list[dict[str, Any]]
    route_refs_json: list[dict[str, Any]]
    dependencies_json: list[dict[str, Any]]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    runtime_availability: CapabilityRuntimeAvailability | None = None


class CapabilitySeedRead(ApiSchema):
    seeded_count: int
    capability_keys: list[str]


class CapabilitySummaryRead(ApiSchema):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_execution_type: dict[str, int]
    by_safety_level: dict[str, int]
    by_runtime_status: dict[str, int]
    requires_external_credentials: int
    requires_database: int
    missing_modules: list[str]
    disabled_modules: list[str]
    provider_backed_modules: list[str]
    safe_to_run_automatically: list[str]


class CapabilityListQuery(ApiSchema):
    category: CapabilityCategory | None = None
    status: CapabilityStatus | None = None
    execution_type: CapabilityExecutionType | None = None
    safety_level: CapabilitySafetyLevel | None = None
    requires_external_credentials: bool | None = None
    include_runtime: bool = True
    limit: int = Field(default=200, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
