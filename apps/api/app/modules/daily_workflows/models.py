from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DailyWorkflowType(StrEnum):
    DAILY_SCAN = "daily_scan"
    SESSION_SCAN = "session_scan"
    WATCHLIST_SCAN = "watchlist_scan"
    DATA_REFRESH_ONLY = "data_refresh_only"


class DailyWorkflowRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DailyWorkflowStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DailyWorkflowStepKey(StrEnum):
    PROVIDER_HEALTH_REFRESH = "provider_health_refresh"
    GAP_RECOVERY_PREPARE = "gap_recovery_prepare"
    SCHEDULED_SCAN_RUN = "scheduled_scan_run"
    SETUP_CONTEXT_GENERATE = "setup_context_generate"
    SIGNAL_PRIORITY_SCORE = "signal_priority_score"
    MARKET_MEMORY_REFRESH = "market_memory_refresh"
    SIGNAL_DIGEST_GENERATE = "signal_digest_generate"
    DAILY_BRIEF_GENERATE = "daily_brief_generate"


class DailyWorkflowRun(Base):
    __tablename__ = "daily_workflow_runs"
    __table_args__ = (
        CheckConstraint(
            "workflow_type in ('daily_scan', 'session_scan', 'watchlist_scan', "
            "'data_refresh_only')",
            name="daily_workflow_runs_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="daily_workflow_runs_status_allowed",
        ),
        Index("ix_daily_workflow_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_daily_workflow_runs_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(32), nullable=False)
    watchlist_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    preference_profile_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("personal_strategy_preference_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    steps_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    result_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_artifact_ids_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class DailyWorkflowStep(Base):
    __tablename__ = "daily_workflow_steps"
    __table_args__ = (
        CheckConstraint(
            "step_key in ('provider_health_refresh', 'gap_recovery_prepare', "
            "'scheduled_scan_run', 'setup_context_generate', 'signal_priority_score', "
            "'market_memory_refresh', 'signal_digest_generate', 'daily_brief_generate')",
            name="daily_workflow_steps_key_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'skipped', 'failed', 'cancelled')",
            name="daily_workflow_steps_status_allowed",
        ),
        Index("ix_daily_workflow_steps_run_key", "workflow_run_id", "step_key"),
        Index("ix_daily_workflow_steps_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("daily_workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    skipped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
