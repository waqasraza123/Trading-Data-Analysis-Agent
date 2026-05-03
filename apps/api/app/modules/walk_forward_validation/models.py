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
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class WalkForwardValidationRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class WalkForwardStabilityLabel(StrEnum):
    STABLE = "stable"
    IMPROVING = "improving"
    DEGRADING = "degrading"
    MIXED = "mixed"
    LOW_SAMPLE = "low_sample"
    INSUFFICIENT_DATA = "insufficient_data"


class WalkForwardValidationRun(Base):
    __tablename__ = "walk_forward_validation_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="walk_forward_validation_runs_status_allowed",
        ),
        CheckConstraint(
            "minimum_sample_size > 0",
            name="walk_forward_validation_runs_minimum_sample_size_positive",
        ),
        CheckConstraint(
            "window_count >= 0 and evaluated_signal_count >= 0 and evaluated_outcome_count >= 0",
            name="walk_forward_validation_runs_counts_non_negative",
        ),
        Index(
            "ix_walk_forward_validation_runs_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    window_config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    window_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    evaluated_signal_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    evaluated_outcome_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class WalkForwardValidationWindow(Base):
    __tablename__ = "walk_forward_validation_windows"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes > 0",
            name="walk_forward_validation_windows_horizon_positive",
        ),
        CheckConstraint(
            "window_index >= 0",
            name="walk_forward_validation_windows_index_non_negative",
        ),
        CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="walk_forward_validation_windows_counts_non_negative",
        ),
        CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="walk_forward_validation_windows_rates_range",
        ),
        CheckConstraint(
            "average_confidence_score is null or "
            "(average_confidence_score >= 0 and average_confidence_score <= 1)",
            name="walk_forward_validation_windows_average_confidence_range",
        ),
        CheckConstraint(
            "confidence_alignment_score is null or "
            "(confidence_alignment_score >= 0 and confidence_alignment_score <= 1)",
            name="walk_forward_validation_windows_alignment_range",
        ),
        CheckConstraint(
            "stability_label in ('stable', 'improving', 'degrading', 'mixed', "
            "'low_sample', 'insufficient_data')",
            name="walk_forward_validation_windows_stability_label_allowed",
        ),
        Index(
            "ix_walk_forward_validation_windows_run_index",
            "validation_run_id",
            "window_index",
        ),
        Index("ix_walk_forward_validation_windows_stability_label", "stability_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    validation_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("walk_forward_validation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
    confidence_alignment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    stability_label: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()


class WalkForwardValidationComparison(Base):
    __tablename__ = "walk_forward_validation_comparisons"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes > 0",
            name="walk_forward_validation_comparisons_horizon_positive",
        ),
        CheckConstraint(
            "compared_window_count >= 0",
            name="walk_forward_validation_comparisons_window_count_non_negative",
        ),
        CheckConstraint(
            "stability_score >= 0 and stability_score <= 1",
            name="walk_forward_validation_comparisons_stability_score_range",
        ),
        Index(
            "ix_walk_forward_validation_comparisons_run_id",
            "validation_run_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    validation_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("walk_forward_validation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    compared_window_count: Mapped[int] = mapped_column(Integer, nullable=False)
    stability_score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    degradation_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    improvement_detected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
