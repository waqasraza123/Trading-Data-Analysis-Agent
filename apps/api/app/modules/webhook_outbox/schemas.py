from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.webhook_outbox.models import (
    WebhookDeliveryAttemptStatus,
    WebhookEventType,
    WebhookOutboxEventStatus,
    WebhookSubscriptionStatus,
)


class WebhookSubscriptionCreate(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    status: WebhookSubscriptionStatus = WebhookSubscriptionStatus.PAUSED
    target_url: str = Field(min_length=1, max_length=2048)
    event_types_json: list[WebhookEventType] = Field(min_length=1)
    signing_secret_ref: str | None = Field(default=None, min_length=1, max_length=255)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_url")
    @classmethod
    def validate_target_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("https://", "http://")):
            msg = "Webhook target URL must use http or https"
            raise ValueError(msg)
        return normalized


class WebhookSubscriptionUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    status: WebhookSubscriptionStatus | None = None
    target_url: str | None = Field(default=None, min_length=1, max_length=2048)
    event_types_json: list[WebhookEventType] | None = Field(default=None, min_length=1)
    signing_secret_ref: str | None = Field(default=None, min_length=1, max_length=255)
    metadata_json: dict[str, Any] | None = None

    @field_validator("target_url")
    @classmethod
    def validate_target_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized.startswith(("https://", "http://")):
            msg = "Webhook target URL must use http or https"
            raise ValueError(msg)
        return normalized


class WebhookSubscriptionRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    status: WebhookSubscriptionStatus
    target_url: str
    event_types_json: list[WebhookEventType]
    signing_secret_ref: str | None
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class WebhookOutboxEventCreate(ApiSchema):
    workspace_id: UUID
    event_type: WebhookEventType
    source_type: str = Field(min_length=1, max_length=80)
    source_id: UUID
    subscription_id: UUID | None = None
    status: WebhookOutboxEventStatus = WebhookOutboxEventStatus.HELD


class WebhookOutboxEventRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    subscription_id: UUID | None
    event_type: WebhookEventType
    source_type: str
    source_id: UUID
    status: WebhookOutboxEventStatus
    payload_json: dict[str, Any]
    redaction_warnings_json: list[str]
    delivery_attempt_count: int
    next_attempt_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryAttemptRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    outbox_event_id: UUID
    status: WebhookDeliveryAttemptStatus
    attempted_at: datetime
    response_status_code: int | None
    error_message: str | None
    metadata_json: dict[str, Any]
