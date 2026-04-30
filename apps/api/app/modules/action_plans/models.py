from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ActionPlanSourceType(StrEnum):
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    OUTCOME = "outcome"
    SCREENSHOT_DECISION = "screenshot_decision"
    REPLAY = "replay"


class ActionPlanStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ActionPlanCreatedFrom(StrEnum):
    SCENARIO_REASONING = "scenario_reasoning"
    DETERMINISTIC_RULES = "deterministic_rules"
    MANUAL_API = "manual_api"


class ReasoningActionType(StrEnum):
    EVALUATE_OUTCOME_AFTER_HORIZON = "evaluate_outcome_after_horizon"
    RUN_REPLAY = "run_replay"
    RUN_NEWS_CORRELATION = "run_news_correlation"
    WAIT_FOR_MORE_FINAL_CANDLES = "wait_for_more_final_candles"
    REQUEST_HUMAN_REVIEW = "request_human_review"
    NO_ACTION = "no_action"


class ReasoningActionItemStatus(StrEnum):
    PENDING = "pending"
    DUE = "due"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReasoningActionWorkerRunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ReasoningActionPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ReasoningActionPlan(Base):
    __tablename__ = "reasoning_action_plans"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', "
            "'screenshot_decision', 'replay')",
            name="reasoning_action_plans_source_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'active', 'completed', 'completed_with_warnings', "
            "'cancelled', 'failed')",
            name="reasoning_action_plans_status_allowed",
        ),
        CheckConstraint(
            "created_from in ('scenario_reasoning', 'deterministic_rules', 'manual_api')",
            name="reasoning_action_plans_created_from_allowed",
        ),
        Index(
            "ix_reasoning_action_plans_workspace_status_created",
            "workspace_id",
            "status",
            "created_at",
        ),
        Index("ix_reasoning_action_plans_reasoning_run_id", "reasoning_run_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
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
    reasoning_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_from: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class ReasoningActionItem(Base):
    __tablename__ = "reasoning_action_items"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', "
            "'screenshot_decision', 'replay')",
            name="reasoning_action_items_source_type_allowed",
        ),
        CheckConstraint(
            "action_type in ('evaluate_outcome_after_horizon', 'run_replay', "
            "'run_news_correlation', 'wait_for_more_final_candles', "
            "'request_human_review', 'no_action')",
            name="reasoning_action_items_action_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'due', 'running', 'completed', 'skipped', "
            "'failed', 'cancelled')",
            name="reasoning_action_items_status_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high')",
            name="reasoning_action_items_priority_allowed",
        ),
        CheckConstraint("attempts >= 0", name="reasoning_action_items_attempts_non_negative"),
        CheckConstraint("max_attempts > 0", name="reasoning_action_items_max_attempts_positive"),
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_reasoning_action_items_workspace_id_idempotency_key",
        ),
        Index("ix_reasoning_action_items_workspace_status_due", "workspace_id", "status", "due_at"),
        Index("ix_reasoning_action_items_signal_action", "signal_id", "action_type"),
        Index("ix_reasoning_action_items_analysis_action", "analysis_run_id", "action_type"),
        Index("ix_reasoning_action_items_reasoning_action", "reasoning_run_id", "action_type"),
        Index("ix_reasoning_action_items_action_status", "action_type", "status"),
        Index("ix_reasoning_action_items_lock", "locked_by", "locked_until"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_plan_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("reasoning_action_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
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
    reasoning_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(48), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    horizon_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(220), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default=text("3"),
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class ReasoningActionWorkerRun(Base):
    __tablename__ = "reasoning_action_worker_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('running', 'completed', 'completed_with_warnings', 'failed')",
            name="reasoning_action_worker_runs_status_allowed",
        ),
        CheckConstraint(
            "batch_limit > 0",
            name="reasoning_action_worker_runs_batch_limit_positive",
        ),
        CheckConstraint(
            "claimed_count >= 0",
            name="reasoning_action_worker_runs_claimed_count_non_negative",
        ),
        CheckConstraint(
            "completed_count >= 0",
            name="reasoning_action_worker_runs_completed_count_non_negative",
        ),
        CheckConstraint(
            "skipped_count >= 0",
            name="reasoning_action_worker_runs_skipped_count_non_negative",
        ),
        CheckConstraint(
            "failed_count >= 0",
            name="reasoning_action_worker_runs_failed_count_non_negative",
        ),
        Index("ix_reasoning_action_worker_runs_workspace_status", "workspace_id", "status"),
        Index("ix_reasoning_action_worker_runs_worker_started", "worker_id", "started_at"),
    )

    id = uuid_primary_key()
    worker_id: Mapped[str] = mapped_column(String(128), nullable=False)
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
        server_default=text("0"),
    )
    completed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
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
