from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class BacktestExperimentRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class BacktestCohortLabel(StrEnum):
    STRONG_FOLLOW_THROUGH = "strong_follow_through"
    MIXED_BEHAVIOR = "mixed_behavior"
    REVERSAL_PRONE = "reversal_prone"
    LOW_SAMPLE = "low_sample"
    INSUFFICIENT_DATA = "insufficient_data"
    NEUTRAL = "neutral"


class BacktestExperimentRun(Base):
    __tablename__ = "backtest_experiment_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="backtest_experiment_runs_status_allowed",
        ),
        CheckConstraint(
            "minimum_sample_size > 0",
            name="backtest_experiment_runs_minimum_sample_size_positive",
        ),
        CheckConstraint(
            "signal_count >= 0 and outcome_count >= 0 and cohort_count >= 0",
            name="backtest_experiment_runs_counts_non_negative",
        ),
        Index(
            "ix_backtest_experiment_runs_workspace_created",
            "workspace_id",
            "created_at",
        ),
        Index("ix_backtest_experiment_runs_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    experiment_version: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    cohort_dimensions_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    outcome_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    cohort_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class BacktestExperimentCohort(Base):
    __tablename__ = "backtest_experiment_cohorts"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes > 0",
            name="backtest_experiment_cohorts_horizon_positive",
        ),
        CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="backtest_experiment_cohorts_counts_non_negative",
        ),
        CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="backtest_experiment_cohorts_rates_range",
        ),
        CheckConstraint(
            "cohort_label in ('strong_follow_through', 'mixed_behavior', 'reversal_prone', "
            "'low_sample', 'insufficient_data', 'neutral')",
            name="backtest_experiment_cohorts_label_allowed",
        ),
        Index("ix_backtest_experiment_cohorts_experiment_run_id", "experiment_run_id"),
        Index("ix_backtest_experiment_cohorts_cohort_key", "cohort_key"),
        Index("ix_backtest_experiment_cohorts_cohort_label", "cohort_label"),
        Index("ix_backtest_experiment_cohorts_horizon_minutes", "horizon_minutes"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    experiment_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("backtest_experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    cohort_key: Mapped[str] = mapped_column(String(500), nullable=False)
    cohort_dimensions_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_count: Mapped[int] = mapped_column(Integer, nullable=False)
    continuation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    partial_follow_through_count: Mapped[int] = mapped_column(Integer, nullable=False)
    no_follow_through_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reversal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    insufficient_data_count: Mapped[int] = mapped_column(Integer, nullable=False)
    continuation_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    reversal_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    no_follow_through_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    average_confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    average_max_favorable_move: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10),
        nullable=True,
    )
    average_max_adverse_move: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10),
        nullable=True,
    )
    average_net_move: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_max_favorable_pips: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10),
        nullable=True,
    )
    average_max_adverse_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_net_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_max_favorable_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_max_adverse_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_net_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    cohort_label: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
