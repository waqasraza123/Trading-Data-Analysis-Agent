from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class AnalysisMode(StrEnum):
    HISTORICAL = "historical"
    LIVE_WINDOW = "live_window"
    SCHEDULED_SCAN = "scheduled_scan"
    REPLAY = "replay"


class AnalysisRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"
    CANCELLED = "cancelled"


class AnalysisReplayMode(StrEnum):
    LATEST_ENGINE_VERSION = "latest_engine_version"
    SAME_ENGINE_VERSION = "same_engine_version"


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (
        CheckConstraint(
            "analysis_mode in ('historical', 'live_window', 'scheduled_scan', 'replay')",
            name="analysis_mode_allowed",
        ),
        CheckConstraint(
            "status in ('queued', 'running', 'completed', 'failed', "
            "'insufficient_data', 'cancelled')",
            name="status_allowed",
        ),
        CheckConstraint(
            "replay_mode is null or replay_mode in "
            "('latest_engine_version', 'same_engine_version')",
            name="replay_mode_allowed",
        ),
        Index("ix_analysis_runs_workspace_id", "workspace_id"),
        Index("ix_analysis_runs_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_analysis_runs_status", "status"),
        Index("ix_analysis_runs_window", "start_time", "end_time"),
        Index("ix_analysis_runs_replayed_from", "replayed_from_analysis_run_id"),
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
    replayed_from_analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    replay_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    warmup_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    baseline_start_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    analysis_mode: Mapped[str] = mapped_column(String(32), nullable=False)
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
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    engine_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_set_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AnalysisAuditLog(Base):
    __tablename__ = "analysis_audit_logs"
    __table_args__ = (
        Index("ix_analysis_audit_logs_analysis_run_id", "analysis_run_id"),
        Index("ix_analysis_audit_logs_event_type", "event_type"),
    )

    id = uuid_primary_key()
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at = created_at_column()
