from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class OutcomeEvaluationStatus(StrEnum):
    PENDING = "pending"
    EVALUATED = "evaluated"
    INSUFFICIENT_FUTURE_DATA = "insufficient_future_data"
    SKIPPED_NOT_DIRECTIONAL = "skipped_not_directional"
    FAILED = "failed"


class OutcomeLabel(StrEnum):
    CONTINUATION = "continuation"
    PARTIAL_FOLLOW_THROUGH = "partial_follow_through"
    NO_FOLLOW_THROUGH = "no_follow_through"
    REVERSAL = "reversal"
    SIDEWAYS_AFTER_SIGNAL = "sideways_after_signal"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_DIRECTIONAL = "not_directional"
    FAILED = "failed"


class OutcomeEvaluationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class OutcomeEvaluationScopeType(StrEnum):
    SINGLE_SIGNAL = "single_signal"
    ANALYSIS_RUN = "analysis_run"
    WORKSPACE_BACKFILL = "workspace_backfill"
    SYMBOL_BACKFILL = "symbol_backfill"
    REPLAY_BACKFILL = "replay_backfill"


class SignalOutcome(Base):
    __tablename__ = "signal_outcomes"
    __table_args__ = (
        CheckConstraint(
            "bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="signal_outcomes_bias_allowed",
        ),
        CheckConstraint(
            "classification_status in ('signal', 'no_signal', 'unclear', 'insufficient_evidence')",
            name="signal_outcomes_classification_status_allowed",
        ),
        CheckConstraint(
            "evaluation_status in ('pending', 'evaluated', 'insufficient_future_data', "
            "'skipped_not_directional', 'failed')",
            name="signal_outcomes_evaluation_status_allowed",
        ),
        CheckConstraint(
            "outcome_label in ('continuation', 'partial_follow_through', 'no_follow_through', "
            "'reversal', 'sideways_after_signal', 'insufficient_data', 'not_directional', "
            "'failed')",
            name="signal_outcomes_outcome_label_allowed",
        ),
        CheckConstraint("horizon_minutes > 0", name="signal_outcomes_horizon_positive"),
        CheckConstraint(
            "future_candle_count >= 0",
            name="signal_outcomes_future_candle_count_non_negative",
        ),
        UniqueConstraint(
            "signal_id",
            "horizon_minutes",
            "evaluation_version",
            name="uq_signal_outcomes_signal_horizon_version",
        ),
        Index("ix_signal_outcomes_signal_horizon", "signal_id", "horizon_minutes"),
        Index(
            "ix_signal_outcomes_workspace_symbol_timeframe_horizon",
            "workspace_id",
            "symbol_id",
            "timeframe",
            "horizon_minutes",
        ),
        Index("ix_signal_outcomes_pattern_horizon", "pattern_type", "horizon_minutes"),
        Index(
            "ix_signal_outcomes_strategy_profile_horizon",
            "strategy_profile_key",
            "horizon_minutes",
        ),
        Index("ix_signal_outcomes_outcome_label", "outcome_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    strategy_profile_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    future_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    future_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    future_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_favorable_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    max_adverse_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    net_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    max_favorable_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    max_adverse_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    net_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    max_favorable_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    max_adverse_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    net_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    direction_followed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reversal_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    outcome_label: Mapped[str] = mapped_column(String(40), nullable=False)
    movement_quality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class OutcomeEvaluationRun(Base):
    __tablename__ = "outcome_evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="outcome_evaluation_runs_status_allowed",
        ),
        CheckConstraint(
            "scope_type in ('single_signal', 'analysis_run', 'workspace_backfill', "
            "'symbol_backfill', 'replay_backfill')",
            name="outcome_evaluation_runs_scope_type_allowed",
        ),
        CheckConstraint(
            "evaluated_count >= 0",
            name="outcome_evaluation_runs_evaluated_count_non_negative",
        ),
        CheckConstraint(
            "skipped_count >= 0",
            name="outcome_evaluation_runs_skipped_count_non_negative",
        ),
        CheckConstraint(
            "failed_count >= 0",
            name="outcome_evaluation_runs_failed_count_non_negative",
        ),
        Index("ix_outcome_evaluation_runs_workspace_status", "workspace_id", "status"),
        Index("ix_outcome_evaluation_runs_scope_type", "scope_type"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    evaluated_count: Mapped[int] = mapped_column(
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
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
