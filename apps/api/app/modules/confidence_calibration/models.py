from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class ConfidenceCalibrationRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ConfidenceCalibrationLabel(StrEnum):
    WELL_ALIGNED = "well_aligned"
    OVERCONFIDENT = "overconfident"
    UNDERCONFIDENT = "underconfident"
    MIXED = "mixed"
    LOW_SAMPLE = "low_sample"
    INSUFFICIENT_DATA = "insufficient_data"


class ConfidenceCalibrationRun(Base):
    __tablename__ = "confidence_calibration_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="confidence_calibration_runs_status_allowed",
        ),
        CheckConstraint(
            "minimum_sample_size > 0",
            name="confidence_calibration_runs_minimum_sample_size_positive",
        ),
        CheckConstraint(
            "evaluated_signal_count >= 0 and evaluated_outcome_count >= 0 and bin_count >= 0",
            name="confidence_calibration_runs_counts_non_negative",
        ),
        Index(
            "ix_confidence_calibration_runs_workspace_created",
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
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    calibration_version: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    bin_config_json: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
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
    bin_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ConfidenceCalibrationBin(Base):
    __tablename__ = "confidence_calibration_bins"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes > 0",
            name="confidence_calibration_bins_horizon_positive",
        ),
        CheckConstraint(
            "bin_min >= 0 and bin_min <= 1 and bin_max >= 0 and bin_max <= 1 "
            "and bin_min <= bin_max",
            name="confidence_calibration_bins_bin_range",
        ),
        CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="confidence_calibration_bins_counts_non_negative",
        ),
        CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="confidence_calibration_bins_rates_range",
        ),
        CheckConstraint(
            "average_confidence_score >= 0 and average_confidence_score <= 1",
            name="confidence_calibration_bins_average_confidence_range",
        ),
        CheckConstraint(
            "confidence_alignment_score >= 0 and confidence_alignment_score <= 1",
            name="confidence_calibration_bins_alignment_range",
        ),
        CheckConstraint(
            "calibration_label in ('well_aligned', 'overconfident', 'underconfident', "
            "'mixed', 'low_sample', 'insufficient_data')",
            name="confidence_calibration_bins_label_allowed",
        ),
        Index("ix_confidence_calibration_bins_run_id", "calibration_run_id"),
        Index(
            "ix_confidence_calibration_bins_horizon_label",
            "horizon_minutes",
            "bin_label",
        ),
        Index("ix_confidence_calibration_bins_calibration_label", "calibration_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    calibration_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("confidence_calibration_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    bin_label: Mapped[str] = mapped_column(String(32), nullable=False)
    bin_min: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    bin_max: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
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
    average_confidence_score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    confidence_alignment_score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    calibration_label: Mapped[str] = mapped_column(String(40), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
