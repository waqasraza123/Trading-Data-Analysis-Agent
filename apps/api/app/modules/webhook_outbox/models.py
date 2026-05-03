from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class WebhookSubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class WebhookOutboxEventStatus(StrEnum):
    PENDING = "pending"
    HELD = "held"
    CANCELLED = "cancelled"
    DELIVERED = "delivered"
    FAILED = "failed"


class WebhookDeliveryAttemptStatus(StrEnum):
    SKIPPED = "skipped"
    FAILED = "failed"
    DELIVERED = "delivered"


class WebhookEventType(StrEnum):
    SIGNAL_CLASSIFIED = "signal.classified"
    OUTCOME_EVALUATED = "outcome.evaluated"
    REASONING_SCENARIOS_GENERATED = "reasoning.scenarios_generated"
    ACTION_PLAN_CREATED = "action_plan.created"
    ACTION_ITEM_COMPLETED = "action_item.completed"
    ACTION_ITEM_FAILED = "action_item.failed"
    QUALITY_FINDING_CREATED = "quality.finding_created"
    READINESS_BLOCKED = "readiness.blocked"
    OPERATOR_REVIEW_OPENED = "operator_review.opened"


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="webhook_subscriptions_status_allowed",
        ),
        Index("ix_webhook_subscriptions_workspace_status", "workspace_id", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    event_types_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    signing_secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class WebhookOutboxEvent(Base):
    __tablename__ = "webhook_outbox_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('signal.classified', 'outcome.evaluated', "
            "'reasoning.scenarios_generated', 'action_plan.created', "
            "'action_item.completed', 'action_item.failed', 'quality.finding_created', "
            "'readiness.blocked', 'operator_review.opened')",
            name="webhook_outbox_events_event_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'held', 'cancelled', 'delivered', 'failed')",
            name="webhook_outbox_events_status_allowed",
        ),
        CheckConstraint(
            "delivery_attempt_count >= 0",
            name="webhook_outbox_events_delivery_attempt_count_non_negative",
        ),
        Index(
            "ix_webhook_outbox_events_workspace_event_status",
            "workspace_id",
            "event_type",
            "status",
        ),
        Index("ix_webhook_outbox_events_source", "source_type", "source_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("webhook_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    redaction_warnings_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    delivery_attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class WebhookDeliveryAttempt(Base):
    __tablename__ = "webhook_delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            "status in ('skipped', 'failed', 'delivered')",
            name="webhook_delivery_attempts_status_allowed",
        ),
        Index("ix_webhook_delivery_attempts_outbox_event_id", "outbox_event_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    outbox_event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("webhook_outbox_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
