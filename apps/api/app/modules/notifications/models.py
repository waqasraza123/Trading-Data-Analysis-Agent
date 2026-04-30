from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationEventType(StrEnum):
    SIGNAL_READY = "signal_ready"
    ANALYSIS_COMPLETED = "analysis_completed"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    OUTCOME_READY = "outcome_ready"
    DIAGNOSTIC_READY = "diagnostic_ready"
    AI_INTELLIGENCE_READY = "ai_intelligence_ready"
    SYSTEM_HEALTH = "system_health"
    MANUAL_OPERATOR_NOTE = "manual_operator_note"


class NotificationSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationStatus(StrEnum):
    QUEUED = "queued"
    SENDING = "sending"
    DELIVERED = "delivered"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationSourceType(StrEnum):
    SYSTEM = "system"
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    ACTION_ITEM = "action_item"
    OUTCOME = "outcome"
    DIAGNOSTIC = "diagnostic"
    AI_INTELLIGENCE = "ai_intelligence"
    SCREENSHOT_DECISION = "screenshot_decision"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        CheckConstraint(
            "channel in ('in_app', 'email', 'webhook')",
            name="notification_preferences_channel_allowed",
        ),
        CheckConstraint(
            "event_type in ('signal_ready', 'analysis_completed', 'human_review_requested', "
            "'outcome_ready', 'diagnostic_ready', 'ai_intelligence_ready', 'system_health', "
            "'manual_operator_note')",
            name="notification_preferences_event_type_allowed",
        ),
        CheckConstraint(
            "min_severity in ('info', 'low', 'medium', 'high')",
            name="notification_preferences_min_severity_allowed",
        ),
        Index(
            "ix_notification_preferences_workspace_user",
            "workspace_id",
            "user_id",
        ),
        Index(
            "uq_notification_preferences_workspace_user_channel_event",
            "workspace_id",
            "user_id",
            "channel",
            "event_type",
            unique=True,
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    min_severity: Mapped[str] = mapped_column(String(16), nullable=False)
    destination_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class NotificationMessage(Base):
    __tablename__ = "notification_messages"
    __table_args__ = (
        CheckConstraint(
            "channel in ('in_app', 'email', 'webhook')",
            name="notification_messages_channel_allowed",
        ),
        CheckConstraint(
            "event_type in ('signal_ready', 'analysis_completed', 'human_review_requested', "
            "'outcome_ready', 'diagnostic_ready', 'ai_intelligence_ready', 'system_health', "
            "'manual_operator_note')",
            name="notification_messages_event_type_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="notification_messages_severity_allowed",
        ),
        CheckConstraint(
            "status in ('queued', 'sending', 'delivered', 'skipped', 'failed', 'cancelled')",
            name="notification_messages_status_allowed",
        ),
        CheckConstraint(
            "source_type in ('system', 'signal', 'analysis_run', 'reasoning_run', "
            "'action_item', 'outcome', 'diagnostic', 'ai_intelligence', 'screenshot_decision')",
            name="notification_messages_source_type_allowed",
        ),
        CheckConstraint("attempts >= 0", name="notification_messages_attempts_non_negative"),
        CheckConstraint("max_attempts > 0", name="notification_messages_max_attempts_positive"),
        Index(
            "uq_notification_messages_workspace_idempotency",
            "workspace_id",
            "idempotency_key",
            unique=True,
        ),
        Index("ix_notification_messages_workspace_status_due", "workspace_id", "status", "due_at"),
        Index("ix_notification_messages_user_status_created", "user_id", "status", "created_at"),
        Index("ix_notification_messages_source", "source_type", "source_id"),
        Index("ix_notification_messages_lock", "locked_by", "locked_until"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(24), nullable=False)
    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    idempotency_key: Mapped[str] = mapped_column(String(220), nullable=False)
    blocked_terms_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    locked_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class NotificationWorkerRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class NotificationWorkerRun(Base):
    __tablename__ = "notification_worker_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('running', 'completed', 'completed_with_warnings', 'failed')",
            name="notification_worker_runs_status_allowed",
        ),
        CheckConstraint("claimed_count >= 0", name="notification_worker_runs_claimed_non_negative"),
        CheckConstraint(
            "delivered_count >= 0",
            name="notification_worker_runs_delivered_non_negative",
        ),
        CheckConstraint("skipped_count >= 0", name="notification_worker_runs_skipped_non_negative"),
        CheckConstraint("failed_count >= 0", name="notification_worker_runs_failed_non_negative"),
        Index("ix_notification_worker_runs_started_at", "started_at"),
        Index("ix_notification_worker_runs_worker_id_started", "worker_id", "started_at"),
    )

    id = uuid_primary_key()
    worker_id: Mapped[str] = mapped_column(String(120), nullable=False)
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    batch_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    claimed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    delivered_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
