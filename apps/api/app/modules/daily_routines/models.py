from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DailyRoutineType(StrEnum):
    PRE_MARKET = "pre_market"
    SESSION_OPEN = "session_open"
    INTRADAY = "intraday"
    CLOSE_OF_DAY = "close_of_day"
    DATA_REPAIR = "data_repair"
    REVIEW = "review"
    CUSTOM = "custom"


class DailyRoutineTemplateStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class DailyRoutineRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DailyRoutineRunStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


class DailyRoutineStepKey(StrEnum):
    PROVIDER_HEALTH_REFRESH = "provider_health_refresh"
    GAP_RECOVERY_PREPARE = "gap_recovery_prepare"
    DAILY_WORKFLOW_RUN = "daily_workflow_run"
    SCHEDULED_SCAN_RUN = "scheduled_scan_run"
    SETUP_CONTEXT_GENERATE = "setup_context_generate"
    SIGNAL_PRIORITY_SCORE = "signal_priority_score"
    MARKET_MEMORY_REFRESH = "market_memory_refresh"
    DIGEST_GENERATE = "digest_generate"
    BRIEF_GENERATE = "brief_generate"
    OUTCOME_REVIEW_COLLECT = "outcome_review_collect"
    QUALITY_SUMMARY_COLLECT = "quality_summary_collect"
    JOURNAL_FOLLOW_UP_COLLECT = "journal_follow_up_collect"
    NOTIFICATION_EVENT_CREATE = "notification_event_create"


class DailyRoutineTemplate(Base):
    __tablename__ = "daily_routine_templates"
    __table_args__ = (
        CheckConstraint(
            "routine_type in ('pre_market', 'session_open', 'intraday', 'close_of_day', "
            "'data_repair', 'review', 'custom')",
            name="daily_routine_templates_type_allowed",
        ),
        CheckConstraint(
            "status in ('active', 'archived')",
            name="daily_routine_templates_status_allowed",
        ),
        Index("ix_daily_routine_templates_workspace_key_status", "workspace_id", "key", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    key: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    routine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    routine_type: Mapped[str] = mapped_column(String(32), nullable=False)
    steps_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    default_filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    schedule_hint_json: Mapped[dict[str, object]] = mapped_column(
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
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class DailyRoutineRun(Base):
    __tablename__ = "daily_routine_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="daily_routine_runs_status_allowed",
        ),
        Index(
            "ix_daily_routine_runs_workspace_template_created",
            "workspace_id",
            "template_id",
            "created_at",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("daily_routine_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    routine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    step_results_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
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
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class DailyRoutineRunStep(Base):
    __tablename__ = "daily_routine_run_steps"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'skipped', 'failed')",
            name="daily_routine_run_steps_status_allowed",
        ),
        Index("ix_daily_routine_run_steps_run_key", "routine_run_id", "step_key"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    routine_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("daily_routine_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    skipped_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
