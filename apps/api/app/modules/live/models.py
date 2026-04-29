from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class LiveFeedSubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"
    STOPPED = "stopped"
    STALE = "stale"


class LiveFeedEventType(StrEnum):
    CANDLE_PARTIAL = "candle_partial"
    CANDLE_FINAL = "candle_final"
    HEARTBEAT = "heartbeat"
    RECONNECT = "reconnect"
    ERROR = "error"
    SNAPSHOT = "snapshot"


class LiveFeedEventProcessingStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"


class LiveFeedSubscription(Base):
    __tablename__ = "live_feed_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'paused', 'failed', 'stopped', 'stale')",
            name="status_allowed",
        ),
        Index("ix_live_feed_subscriptions_workspace_id", "workspace_id"),
        Index("ix_live_feed_subscriptions_source_id", "source_id"),
        Index("ix_live_feed_subscriptions_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_live_feed_subscriptions_status", "status"),
        Index("ix_live_feed_subscriptions_lease", "worker_id", "lease_expires_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_final_candle_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class LiveFeedEvent(Base):
    __tablename__ = "live_feed_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('candle_partial', 'candle_final', 'heartbeat', "
            "'reconnect', 'error', 'snapshot')",
            name="event_type_allowed",
        ),
        CheckConstraint(
            "processing_status in ('received', 'processed', 'ignored', 'failed')",
            name="processing_status_allowed",
        ),
        Index("ix_live_feed_events_workspace_id", "workspace_id"),
        Index("ix_live_feed_events_source_id", "source_id"),
        Index("ix_live_feed_events_subscription_id", "subscription_id"),
        Index("ix_live_feed_events_received_at", "received_at"),
        Index("ix_live_feed_events_processing_status", "processing_status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("live_feed_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payload_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at = created_at_column()
