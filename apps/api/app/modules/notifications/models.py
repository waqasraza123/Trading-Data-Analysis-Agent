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


class NotificationDeliveryChannelType(StrEnum):
    WEBHOOK = "webhook"
    EMAIL = "email"
    TELEGRAM = "telegram"
    DISCORD = "discord"


class NotificationChannelStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class BackendNotificationEventType(StrEnum):
    SIGNAL_CLASSIFIED = "signal.classified"
    SIGNAL_REVIEW_RECOMMENDED = "signal.review_recommended"
    OUTCOME_EVALUATED = "outcome.evaluated"
    DIGEST_CREATED = "digest.created"
    DATA_QUALITY_DEGRADED = "data_quality.degraded"
    MARKET_MEMORY_STALE = "market_memory.stale"
    REASONING_ACTION_DUE = "reasoning.action_due"
    READINESS_BLOCKED = "readiness.blocked"
    OPERATOR_REVIEW_OPENED = "operator_review.opened"
    SCAN_COMPLETED = "scan.completed"
    PROVIDER_HEALTH_DEGRADED = "provider_health.degraded"
    GAP_RECOVERY_NEEDED = "gap_recovery.needed"


class NotificationEventSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationEventStatus(StrEnum):
    PENDING = "pending"
    HELD = "held"
    DELIVERED = "delivered"
    PARTIALLY_DELIVERED = "partially_delivered"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    FAILED = "failed"


class NotificationInboxStatus(StrEnum):
    UNREAD = "unread"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    ARCHIVED = "archived"


class NotificationDeliveryAttemptStatus(StrEnum):
    PENDING = "pending"
    DELIVERED = "delivered"
    SKIPPED = "skipped"
    FAILED = "failed"
    BLOCKED = "blocked"


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


class NotificationDeliveryChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (
        CheckConstraint(
            "channel_type in ('webhook', 'email', 'telegram', 'discord')",
            name="notification_channels_channel_type_allowed",
        ),
        CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="notification_channels_status_allowed",
        ),
        Index(
            "ix_notification_channels_workspace_status_channel_type",
            "workspace_id",
            "status",
            "channel_type",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    credential_ref_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_credential_refs.id", ondelete="SET NULL"),
        nullable=True,
    )
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_types_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    severity_filter_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    quiet_hours_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('signal.classified', 'signal.review_recommended', "
            "'outcome.evaluated', 'digest.created', 'data_quality.degraded', "
            "'market_memory.stale', 'reasoning.action_due', 'readiness.blocked', "
            "'operator_review.opened', 'scan.completed', 'provider_health.degraded', "
            "'gap_recovery.needed')",
            name="notification_events_event_type_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="notification_events_severity_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'held', 'delivered', 'partially_delivered', "
            "'blocked', 'cancelled', 'failed')",
            name="notification_events_status_allowed",
        ),
        CheckConstraint(
            "safety_status in ('passed', 'blocked', 'redacted', 'review_recommended')",
            name="notification_events_safety_status_allowed",
        ),
        CheckConstraint(
            "inbox_status in ('unread', 'read', 'acknowledged', 'archived')",
            name="notification_events_inbox_status_allowed",
        ),
        Index(
            "ix_notification_events_workspace_event_status",
            "workspace_id",
            "event_type",
            "status",
        ),
        Index(
            "ix_notification_events_workspace_inbox_status_created",
            "workspace_id",
            "inbox_status",
            "created_at",
        ),
        Index("ix_notification_events_source", "source_type", "source_id"),
        Index("ix_notification_events_dedupe_key", "dedupe_key"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(220), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    acknowledged_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    inbox_status: Mapped[str] = mapped_column(
        String(24),
        nullable=False,
        default=NotificationInboxStatus.UNREAD.value,
        server_default=NotificationInboxStatus.UNREAD.value,
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'delivered', 'skipped', 'failed', 'blocked')",
            name="notification_delivery_attempts_status_allowed",
        ),
        Index("ix_notification_delivery_attempts_notification_event_id", "notification_event_id"),
        Index(
            "ix_notification_delivery_attempts_channel_status",
            "channel_id",
            "status",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    notification_event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("notification_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("notification_channels.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
