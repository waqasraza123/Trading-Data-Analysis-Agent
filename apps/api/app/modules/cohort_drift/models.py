from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class CohortDriftRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class CohortDriftLabel(StrEnum):
    NO_DRIFT = "no_drift"
    MILD_DRIFT = "mild_drift"
    MODERATE_DRIFT = "moderate_drift"
    SEVERE_DRIFT = "severe_drift"
    LOW_SAMPLE = "low_sample"
    INSUFFICIENT_DATA = "insufficient_data"


class CohortDriftSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CohortDriftRun(Base):
    __tablename__ = "cohort_drift_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="cohort_drift_runs_status_allowed",
        ),
        CheckConstraint(
            "minimum_sample_size > 0",
            name="cohort_drift_runs_minimum_sample_size_positive",
        ),
        CheckConstraint(
            "cohort_count >= 0 and drift_detected_count >= 0",
            name="cohort_drift_runs_counts_non_negative",
        ),
        Index("ix_cohort_drift_runs_workspace_created", "workspace_id", "created_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    drift_version: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    baseline_window_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    comparison_window_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    cohort_dimensions_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    cohort_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    drift_detected_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class CohortDriftResult(Base):
    __tablename__ = "cohort_drift_results"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes > 0",
            name="cohort_drift_results_horizon_positive",
        ),
        CheckConstraint(
            "baseline_sample_size >= 0 and comparison_sample_size >= 0",
            name="cohort_drift_results_sample_sizes_non_negative",
        ),
        CheckConstraint(
            "drift_score >= 0 and drift_score <= 1",
            name="cohort_drift_results_drift_score_range",
        ),
        CheckConstraint(
            "drift_label in ('no_drift', 'mild_drift', 'moderate_drift', 'severe_drift', "
            "'low_sample', 'insufficient_data')",
            name="cohort_drift_results_label_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="cohort_drift_results_severity_allowed",
        ),
        CheckConstraint(
            "(baseline_continuation_rate is null or "
            "(baseline_continuation_rate >= 0 and baseline_continuation_rate <= 1)) and "
            "(comparison_continuation_rate is null or "
            "(comparison_continuation_rate >= 0 and comparison_continuation_rate <= 1)) and "
            "(baseline_reversal_rate is null or "
            "(baseline_reversal_rate >= 0 and baseline_reversal_rate <= 1)) and "
            "(comparison_reversal_rate is null or "
            "(comparison_reversal_rate >= 0 and comparison_reversal_rate <= 1)) and "
            "(baseline_no_follow_through_rate is null or "
            "(baseline_no_follow_through_rate >= 0 and baseline_no_follow_through_rate <= 1)) and "
            "(comparison_no_follow_through_rate is null or "
            "(comparison_no_follow_through_rate >= 0 and "
            "comparison_no_follow_through_rate <= 1)) and "
            "(baseline_confidence_alignment is null or "
            "(baseline_confidence_alignment >= 0 and baseline_confidence_alignment <= 1)) and "
            "(comparison_confidence_alignment is null or "
            "(comparison_confidence_alignment >= 0 and comparison_confidence_alignment <= 1))",
            name="cohort_drift_results_nullable_rates_range",
        ),
        Index("ix_cohort_drift_results_drift_run_id", "drift_run_id"),
        Index("ix_cohort_drift_results_drift_label", "drift_label"),
        Index("ix_cohort_drift_results_severity", "severity"),
        Index("ix_cohort_drift_results_cohort_key", "cohort_key"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    drift_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("cohort_drift_runs.id", ondelete="CASCADE"),
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
    baseline_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    comparison_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_continuation_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    comparison_continuation_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    continuation_rate_delta: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    baseline_reversal_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    comparison_reversal_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    reversal_rate_delta: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    baseline_no_follow_through_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    comparison_no_follow_through_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    no_follow_through_delta: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    baseline_confidence_alignment: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    comparison_confidence_alignment: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    confidence_alignment_delta: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    drift_score: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    drift_label: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
