from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DailyBriefType(StrEnum):
    DAILY = "daily"
    SESSION = "session"
    INTRADAY = "intraday"
    WATCHLIST = "watchlist"
    CUSTOM_PERIOD = "custom_period"


class DailyBriefStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class DailyBriefItemType(StrEnum):
    REVIEW_FIRST = "review_first"
    NEEDS_CONFIRMATION = "needs_confirmation"
    AVOID_CONDITION = "avoid_condition"
    STALE_DATA = "stale_data"
    OUTCOME_UPDATE = "outcome_update"
    WATCH_NEXT = "watch_next"
    PENDING_ACTION = "pending_action"
    MARKET_CONTEXT = "market_context"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    JOURNAL_FOLLOW_UP = "journal_follow_up"


class DailyBriefPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class DailyBriefRun(Base):
    __tablename__ = "daily_brief_runs"
    __table_args__ = (
        CheckConstraint(
            "brief_type in ('daily', 'session', 'intraday', 'watchlist', 'custom_period')",
            name="daily_brief_runs_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="daily_brief_runs_status_allowed",
        ),
        Index(
            "ix_daily_brief_runs_workspace_type_generated",
            "workspace_id",
            "brief_type",
            "generated_at",
        ),
        Index("ix_daily_brief_runs_watchlist_generated", "watchlist_id", "generated_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    digest_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_digest_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    watchlist_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    brief_type: Mapped[str] = mapped_column(String(32), nullable=False)
    brief_version: Mapped[str] = mapped_column(String(32), nullable=False)
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
    sections_json: Mapped[dict[str, object]] = mapped_column(
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
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()


class DailyBriefItem(Base):
    __tablename__ = "daily_brief_items"
    __table_args__ = (
        CheckConstraint(
            "item_type in ('review_first', 'needs_confirmation', 'avoid_condition', "
            "'stale_data', 'outcome_update', 'watch_next', 'pending_action', "
            "'market_context', 'data_quality_issue', 'journal_follow_up')",
            name="daily_brief_items_type_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="daily_brief_items_priority_allowed",
        ),
        Index("ix_daily_brief_items_run_type", "brief_run_id", "item_type"),
        Index("ix_daily_brief_items_workspace_priority", "workspace_id", "priority"),
        Index("ix_daily_brief_items_signal_id", "signal_id"),
        Index("ix_daily_brief_items_symbol_id", "symbol_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    brief_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("daily_brief_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
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
    setup_context_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("setup_contexts.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
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
