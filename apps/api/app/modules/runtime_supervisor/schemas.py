from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.runtime_supervisor.models import (
    RuntimeRunRequestStatus,
    RuntimeRunRequestType,
    RuntimeWorkerDefinitionStatus,
    RuntimeWorkerInstanceStatus,
    RuntimeWorkerType,
)


class RuntimeWorkerSeedResponse(ApiSchema):
    seeded_count: int
    updated_count: int
    worker_keys: list[str]


class RuntimeWorkerDefinitionRead(ApiReadSchema):
    id: UUID
    key: str
    name: str
    description: str
    worker_type: RuntimeWorkerType
    status: RuntimeWorkerDefinitionStatus
    command: str
    required_settings_json: list[str]
    optional_settings_json: list[str]
    safety_notes_json: list[str]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RuntimeWorkerInstanceRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    worker_definition_key: str
    worker_id: str
    status: RuntimeWorkerInstanceStatus
    host_name: str | None
    process_id: int | None
    started_at: datetime | None
    last_heartbeat_at: datetime | None
    stopped_at: datetime | None
    heartbeat_payload_json: dict[str, Any]
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class RuntimeWorkerInstanceHeartbeat(ApiSchema):
    worker_definition_key: str = Field(min_length=1, max_length=120)
    worker_id: str = Field(min_length=1, max_length=160)
    workspace_id: UUID | None = None
    status: RuntimeWorkerInstanceStatus = RuntimeWorkerInstanceStatus.RUNNING
    host_name: str | None = Field(default=None, max_length=160)
    process_id: int | None = Field(default=None, ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("worker_definition_key", "worker_id", "host_name")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            msg = "Text fields must not be blank"
            raise ValueError(msg)
        return normalized


class RuntimeMarkStaleResponse(ApiSchema):
    stale_count: int
    stale_worker_ids: list[str]
    stale_before: datetime


class RuntimeRunRequestCreate(ApiSchema):
    worker_definition_key: str = Field(min_length=1, max_length=120)
    request_type: RuntimeRunRequestType
    workspace_id: UUID | None = None
    requested_by_user_id: UUID | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("worker_definition_key")
    @classmethod
    def normalize_worker_definition_key(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            msg = "worker_definition_key must not be blank"
            raise ValueError(msg)
        return normalized


class RuntimeRunRequestRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    worker_definition_key: str
    status: RuntimeRunRequestStatus
    requested_by_user_id: UUID | None
    request_type: RuntimeRunRequestType
    input_json: dict[str, Any]
    result_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class RuntimeHealthWorkerSummary(ApiSchema):
    key: str
    name: str
    worker_type: RuntimeWorkerType
    definition_status: RuntimeWorkerDefinitionStatus
    enabled: bool
    running_instances: int
    stale_instances: int
    last_heartbeat_at: datetime | None
    pending_run_requests: int
    running_run_requests: int
    failed_run_requests: int


class RuntimeSupervisorHealth(ApiSchema):
    status: str
    supervisor_version: str
    heartbeat_enabled: bool
    run_requests_enabled: bool
    stale_after_seconds: int
    worker_count: int
    available_worker_count: int
    disabled_worker_count: int
    running_instance_count: int
    stale_instance_count: int
    pending_run_request_count: int
    running_run_request_count: int
    failed_run_request_count: int
    workers: list[RuntimeHealthWorkerSummary]
    operation_counts: dict[str, dict[str, int]]
