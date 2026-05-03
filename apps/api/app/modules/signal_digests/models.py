from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class SignalDigestType(StrEnum):
    DAILY = "daily"
    SESSION = "session"
    CUSTOM_PERIOD = "custom_period"
    WATCHLIST = "watchlist"


class SignalDigestStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class SignalDigestItemType(StrEnum):
    TOP_BIAS = "top_bias"
    NO_SIGNAL = "no_signal"
    REVIEW_RECOMMENDED = "review_recommended"
    DATA_QUALITY_WARNING = "data_quality_warning"
    OUTCOME_UPDATE = "outcome_update"
    NEWS_CONTEXT = "news_context"
    PENDING_ACTION = "pending_action"
    CONFLICT = "conflict"
    STALE_DATA = "stale_data"
    WATCH_CONDITION = "watch_condition"


class SignalDigestPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class SignalDigestRun(Base):
    __tablename__ = "signal_digest_runs"
    __table_args__ = (
        CheckConstraint(
            "digest_type in ('daily', 'session', 'custom_period', 'watchlist')",
            name="signal_digest_runs_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="signal_digest_runs_status_allowed",
        ),
        Index(
            "ix_signal_digest_runs_workspace_type_created",
            "workspace_id",
            "digest_type",
            "created_at",
        ),
        Index("ix_signal_digest_runs_period", "period_start", "period_end"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    digest_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    digest_version: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    section_counts_json: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class SignalDigestItem(Base):
    __tablename__ = "signal_digest_items"
    __table_args__ = (
        CheckConstraint(
            "item_type in ('top_bias', 'no_signal', 'review_recommended', "
            "'data_quality_warning', 'outcome_update', 'news_context', 'pending_action', "
            "'conflict', 'stale_data', 'watch_condition')",
            name="signal_digest_items_type_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="signal_digest_items_priority_allowed",
        ),
        Index("ix_signal_digest_items_run_type", "digest_run_id", "item_type"),
        Index("ix_signal_digest_items_symbol_id", "symbol_id"),
        Index("ix_signal_digest_items_signal_id", "signal_id"),
        Index("ix_signal_digest_items_priority", "priority"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    digest_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_digest_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_item_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("reasoning_action_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    news_event_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at = created_at_column()
