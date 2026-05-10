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


class PatternAttributionRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class PatternAttributionLabel(StrEnum):
    STRONG_SELECTED_BEHAVIOR = "strong_selected_behavior"
    OFTEN_REJECTED = "often_rejected"
    REVERSAL_PRONE = "reversal_prone"
    BLOCKING_EFFECTIVE = "blocking_effective"
    MIXED = "mixed"
    LOW_SAMPLE = "low_sample"
    INSUFFICIENT_DATA = "insufficient_data"


class PatternAttributionRun(Base):
    __tablename__ = "pattern_attribution_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="pattern_attribution_runs_status_allowed",
        ),
        CheckConstraint(
            "minimum_sample_size > 0",
            name="pattern_attribution_runs_minimum_sample_size_positive",
        ),
        CheckConstraint(
            "evaluated_candidate_count >= 0 and evaluated_signal_count >= 0 and result_count >= 0",
            name="pattern_attribution_runs_counts_non_negative",
        ),
        Index(
            "ix_pattern_attribution_runs_workspace_created",
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
    attribution_version: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    minimum_sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_candidate_count: Mapped[int] = mapped_column(
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
    result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class PatternAttributionResult(Base):
    __tablename__ = "pattern_attribution_results"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="pattern_attribution_results_horizon_positive",
        ),
        CheckConstraint(
            "candidate_count >= 0 and selected_count >= 0 and rejected_count >= 0 "
            "and blocked_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="pattern_attribution_results_counts_non_negative",
        ),
        CheckConstraint(
            "average_strength_score is null or "
            "(average_strength_score >= 0 and average_strength_score <= 1)",
            name="pattern_attribution_results_average_strength_range",
        ),
        CheckConstraint(
            "average_selected_confidence is null or "
            "(average_selected_confidence >= 0 and average_selected_confidence <= 1)",
            name="pattern_attribution_results_average_selected_confidence_range",
        ),
        CheckConstraint(
            "continuation_rate is null or (continuation_rate >= 0 and continuation_rate <= 1)",
            name="pattern_attribution_results_continuation_rate_range",
        ),
        CheckConstraint(
            "reversal_rate is null or (reversal_rate >= 0 and reversal_rate <= 1)",
            name="pattern_attribution_results_reversal_rate_range",
        ),
        CheckConstraint(
            "no_follow_through_rate is null or "
            "(no_follow_through_rate >= 0 and no_follow_through_rate <= 1)",
            name="pattern_attribution_results_no_follow_through_rate_range",
        ),
        CheckConstraint(
            "attribution_label in ('strong_selected_behavior', 'often_rejected', "
            "'reversal_prone', 'blocking_effective', 'mixed', 'low_sample', "
            "'insufficient_data')",
            name="pattern_attribution_results_label_allowed",
        ),
        Index("ix_pattern_attribution_results_run_id", "attribution_run_id"),
        Index("ix_pattern_attribution_results_pattern_type", "pattern_type"),
        Index("ix_pattern_attribution_results_label", "attribution_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    attribution_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("pattern_attribution_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    horizon_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False)
    average_strength_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    average_selected_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
    )
    continuation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    partial_follow_through_count: Mapped[int] = mapped_column(Integer, nullable=False)
    no_follow_through_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reversal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    insufficient_data_count: Mapped[int] = mapped_column(Integer, nullable=False)
    continuation_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    reversal_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    no_follow_through_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    attribution_label: Mapped[str] = mapped_column(String(40), nullable=False)
    diagnostic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
