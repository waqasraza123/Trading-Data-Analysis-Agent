from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.job_queue.models import (
    JobQueueDefinitionStatus,
    JobQueueEventType,
    JobQueueItemStatus,
    JobQueueJobType,
    JobQueuePriority,
)


class JobQueueDefinitionRead(ApiReadSchema):
    id: UUID
    key: str
    name: str
    description: str
    status: JobQueueDefinitionStatus
    queue_name: str
    job_type: JobQueueJobType
    max_attempts: int
    default_priority: JobQueuePriority
    timeout_seconds: int | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JobQueueSeedDefinitionsResponse(ApiSchema):
    seeded_count: int
    updated_count: int
    definition_keys: list[str]


class JobQueueJobCreate(ApiSchema):
    workspace_id: UUID | None = None
    queue_name: str | None = Field(default=None, min_length=1, max_length=120)
    job_type: JobQueueJobType
    priority: JobQueuePriority | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=240)
    scheduled_at: datetime | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int | None = Field(default=None, ge=1, le=100)
    force: bool = False

    @field_validator("queue_name", "idempotency_key")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            msg = "Text fields must not be blank"
            raise ValueError(msg)
        return normalized


class JobQueueJobRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    queue_name: str
    job_type: JobQueueJobType
    status: JobQueueItemStatus
    priority: JobQueuePriority
    idempotency_key: str | None
    scheduled_at: datetime | None
    available_at: datetime | None
    locked_by: str | None
    locked_until: datetime | None
    attempts: int
    max_attempts: int
    payload_json: dict[str, Any]
    result_json: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class JobQueueEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    job_id: UUID
    event_type: JobQueueEventType
    message: str
    metadata_json: dict[str, Any]
    created_at: datetime


class JobQueueCancelRequest(ApiSchema):
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
