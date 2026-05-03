from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.engine_executions.models import (
    EngineExecutionEventType,
    EngineExecutionPriority,
    EngineExecutionStatus,
)


class EngineExecutionCreate(ApiSchema):
    workspace_id: UUID
    engine_name: str = Field(min_length=1, max_length=120)
    engine_version: str | None = Field(default=None, max_length=80)
    operation_type: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=1, max_length=240)
    priority: EngineExecutionPriority | None = None
    source_type: str | None = Field(default=None, max_length=80)
    source_id: UUID | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int | None = Field(default=None, ge=1, le=100)
    force: bool = False

    @field_validator(
        "engine_name",
        "operation_type",
        "idempotency_key",
        "engine_version",
        "source_type",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            msg = "Text fields must not be blank"
            raise ValueError(msg)
        return normalized


class EngineExecutionRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    engine_name: str
    engine_version: str | None
    operation_type: str
    idempotency_key: str
    status: EngineExecutionStatus
    priority: EngineExecutionPriority
    source_type: str | None
    source_id: UUID | None
    input_json: dict[str, Any]
    output_json: dict[str, Any] | None
    produced_artifacts_json: list[dict[str, Any]] | None
    error_code: str | None
    error_message: str | None
    attempts: int
    max_attempts: int
    locked_by: str | None
    locked_until: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EngineExecutionEventCreate(ApiSchema):
    event_type: EngineExecutionEventType
    message: str = Field(min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class EngineExecutionEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    execution_record_id: UUID
    event_type: EngineExecutionEventType
    message: str
    metadata_json: dict[str, Any]
    created_at: datetime


class EngineExecutionComplete(ApiSchema):
    output_json: dict[str, Any] = Field(default_factory=dict)
    produced_artifacts_json: list[dict[str, Any]] = Field(default_factory=list)
    completed_with_warnings: bool = False


class EngineExecutionFailure(ApiSchema):
    error_code: str = Field(min_length=1, max_length=120)
    error_message: str = Field(min_length=1)


class EngineExecutionSkip(ApiSchema):
    reason: str = Field(min_length=1)
