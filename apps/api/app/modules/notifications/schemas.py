from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.notifications.models import (
    NotificationChannel,
    NotificationEventType,
    NotificationSeverity,
    NotificationSourceType,
    NotificationStatus,
    NotificationWorkerRunStatus,
)


class NotificationPreferenceUpsert(ApiSchema):
    workspace_id: UUID
    user_id: UUID
    channel: NotificationChannel = NotificationChannel.IN_APP
    event_type: NotificationEventType
    is_enabled: bool = True
    min_severity: NotificationSeverity = NotificationSeverity.INFO
    destination_json: dict[str, Any] = Field(default_factory=dict)


class NotificationPreferenceRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    channel: NotificationChannel
    event_type: NotificationEventType
    is_enabled: bool
    min_severity: NotificationSeverity
    destination_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class NotificationCreateRequest(ApiSchema):
    workspace_id: UUID
    user_id: UUID | None = None
    channel: NotificationChannel = NotificationChannel.IN_APP
    event_type: NotificationEventType
    severity: NotificationSeverity = NotificationSeverity.INFO
    source_type: NotificationSourceType = NotificationSourceType.SYSTEM
    source_id: UUID | None = None
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1, max_length=5000)
    payload_json: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=220)
    due_at: datetime | None = None
    max_attempts: int = Field(default=3, ge=1, le=25)


class NotificationRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None
    channel: NotificationChannel
    event_type: NotificationEventType
    severity: NotificationSeverity
    status: NotificationStatus
    source_type: NotificationSourceType
    source_id: UUID | None
    title: str
    body: str
    payload_json: dict[str, Any]
    idempotency_key: str
    blocked_terms_json: list[str]
    result_json: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    attempts: int
    max_attempts: int
    due_at: datetime | None
    last_attempted_at: datetime | None
    locked_by: str | None
    locked_until: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationDispatchRequest(ApiSchema):
    workspace_id: UUID | None = None
    limit: int = Field(default=100, ge=1, le=500)


class NotificationDispatchResult(ApiSchema):
    message: NotificationRead
    delivered: bool
    skipped: bool
    failed: bool


class NotificationDispatchResponse(ApiSchema):
    claimed_count: int
    delivered_count: int
    skipped_count: int
    failed_count: int
    messages: list[NotificationDispatchResult]


class NotificationWorkerRunRead(ApiReadSchema):
    id: UUID
    worker_id: str
    workspace_id: UUID | None
    status: NotificationWorkerRunStatus
    batch_limit: int
    claimed_count: int
    delivered_count: int
    skipped_count: int
    failed_count: int
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class NotificationWorkerStatusRead(ApiSchema):
    queued_count: int
    sending_count: int
    delivered_count: int
    failed_count: int
    oldest_due_at: datetime | None
    worker_enabled: bool
    last_worker_run: NotificationWorkerRunRead | None = None
