from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class MarketWatchlistStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ScheduledScanMode(StrEnum):
    WATCHLIST = "watchlist"
    SINGLE_SYMBOL = "single_symbol"


class ScheduledScanConfigStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ScheduledScanRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    SKIPPED = "skipped"


class ScheduledScanRunItemStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class MarketWatchlist(Base):
    __tablename__ = "market_watchlists"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="market_watchlists_status_allowed",
        ),
        Index("ix_market_watchlists_workspace_status", "workspace_id", "status"),
        Index("ix_market_watchlists_workspace_name", "workspace_id", "name"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class MarketWatchlistItem(Base):
    __tablename__ = "market_watchlist_items"
    __table_args__ = (
        UniqueConstraint(
            "watchlist_id",
            "symbol_id",
            "source_id",
            "timeframe",
            name="uq_market_watchlist_items_watchlist_symbol_source_timeframe",
        ),
        Index("ix_market_watchlist_items_workspace_watchlist", "workspace_id", "watchlist_id"),
        Index("ix_market_watchlist_items_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_market_watchlist_items_is_active", "is_active"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    watchlist_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlists.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    include_partial_live_candle: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class ScheduledScanConfig(Base):
    __tablename__ = "scheduled_scan_configs"
    __table_args__ = (
        CheckConstraint(
            "scan_mode in ('watchlist', 'single_symbol')",
            name="scheduled_scan_configs_scan_mode_allowed",
        ),
        CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="scheduled_scan_configs_status_allowed",
        ),
        CheckConstraint("lookback_minutes > 0", name="scheduled_scan_configs_lookback_positive"),
        CheckConstraint("interval_seconds > 0", name="scheduled_scan_configs_interval_positive"),
        CheckConstraint(
            "((scan_mode = 'watchlist' and watchlist_id is not null) or "
            "(scan_mode = 'single_symbol' and symbol_id is not null and timeframe is not null))",
            name="scheduled_scan_configs_mode_fields_required",
        ),
        Index(
            "ix_scheduled_scan_configs_workspace_status_next_run",
            "workspace_id",
            "status",
            "next_run_at",
        ),
        Index("ix_scheduled_scan_configs_watchlist_id", "watchlist_id"),
        Index("ix_scheduled_scan_configs_symbol_timeframe", "symbol_id", "timeframe"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    watchlist_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scan_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    lookback_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    include_partial_live_candle: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    include_news_correlation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    include_ai_explanation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    include_reasoning: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    include_action_plan: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class ScheduledScanRun(Base):
    __tablename__ = "scheduled_scan_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'skipped')",
            name="scheduled_scan_runs_status_allowed",
        ),
        CheckConstraint(
            "scan_mode in ('watchlist', 'single_symbol')",
            name="scheduled_scan_runs_scan_mode_allowed",
        ),
        Index("ix_scheduled_scan_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_scheduled_scan_runs_config_created", "scan_config_id", "created_at"),
        Index("ix_scheduled_scan_runs_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_config_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scheduled_scan_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scan_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scanned_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_run_ids_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    signal_ids_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    reasoning_run_ids_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    action_plan_ids_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    result_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class ScheduledScanRunItem(Base):
    __tablename__ = "scheduled_scan_run_items"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'skipped', 'failed')",
            name="scheduled_scan_run_items_status_allowed",
        ),
        Index("ix_scheduled_scan_run_items_scan_run_id", "scan_run_id"),
        Index("ix_scheduled_scan_run_items_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_scheduled_scan_run_items_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scheduled_scan_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_config_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scheduled_scan_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    watchlist_item_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlist_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    reasoning_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_plan_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("reasoning_action_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    skipped_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
