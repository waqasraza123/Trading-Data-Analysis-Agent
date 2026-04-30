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


class DiagnosticRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class DiagnosticScopeType(StrEnum):
    WORKSPACE = "workspace"
    STRATEGY_PROFILE = "strategy_profile"
    SYMBOL = "symbol"
    TIMEFRAME = "timeframe"
    PATTERN = "pattern"
    CUSTOM = "custom"


class DiagnosticLabel(StrEnum):
    STRONG_FOLLOW_THROUGH = "strong_follow_through"
    MIXED_BEHAVIOR = "mixed_behavior"
    REVERSAL_PRONE = "reversal_prone"
    LOW_SAMPLE = "low_sample"
    INSUFFICIENT_DATA = "insufficient_data"
    NEEDS_THRESHOLD_REVIEW = "needs_threshold_review"
    NEUTRAL = "neutral"


class CalibrationRecommendationType(StrEnum):
    REVIEW_MINIMUM_CONFIDENCE = "review_minimum_confidence"
    REVIEW_CANDIDATE_STRENGTH = "review_candidate_strength"
    TIGHTEN_PROFILE_FILTER = "tighten_profile_filter"
    LOOSEN_PROFILE_FILTER = "loosen_profile_filter"
    REVIEW_PATTERN_DETECTOR = "review_pattern_detector"
    INCREASE_SAMPLE_SIZE = "increase_sample_size"
    MONITOR_SYMBOL_TIMEFRAME = "monitor_symbol_timeframe"
    NO_CHANGE = "no_change"


class CalibrationRecommendationSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CalibrationRecommendationStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    APPLIED_MANUALLY = "applied_manually"


class StrategyProfileDiagnosticRun(Base):
    __tablename__ = "strategy_profile_diagnostic_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="strategy_profile_diagnostic_runs_status_allowed",
        ),
        CheckConstraint(
            "scope_type in ('workspace', 'strategy_profile', 'symbol', 'timeframe', "
            "'pattern', 'custom')",
            name="strategy_profile_diagnostic_runs_scope_type_allowed",
        ),
        CheckConstraint(
            "minimum_sample_size > 0",
            name="strategy_profile_diagnostic_runs_minimum_sample_size_positive",
        ),
        CheckConstraint(
            "evaluated_signal_count >= 0",
            name="strategy_profile_diagnostic_runs_evaluated_signal_count_non_negative",
        ),
        CheckConstraint(
            "evaluated_outcome_count >= 0",
            name="strategy_profile_diagnostic_runs_evaluated_outcome_count_non_negative",
        ),
        CheckConstraint(
            "diagnostics_created_count >= 0",
            name="strategy_profile_diagnostic_runs_diagnostics_created_count_non_negative",
        ),
        CheckConstraint(
            "recommendations_created_count >= 0",
            name="strategy_profile_diagnostic_runs_recommendations_created_count_non_negative",
        ),
        Index(
            "ix_strategy_profile_diagnostic_runs_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
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
    diagnostics_created_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    recommendations_created_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class StrategyProfileDiagnostic(Base):
    __tablename__ = "strategy_profile_diagnostics"
    __table_args__ = (
        CheckConstraint(
            "horizon_minutes > 0", name="strategy_profile_diagnostics_horizon_positive"
        ),
        CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="strategy_profile_diagnostics_counts_non_negative",
        ),
        CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="strategy_profile_diagnostics_rates_range",
        ),
        CheckConstraint(
            "confidence_alignment_score is null or "
            "(confidence_alignment_score >= 0 and confidence_alignment_score <= 1)",
            name="strategy_profile_diagnostics_confidence_alignment_range",
        ),
        CheckConstraint(
            "diagnostic_label in ('strong_follow_through', 'mixed_behavior', 'reversal_prone', "
            "'low_sample', 'insufficient_data', 'needs_threshold_review', 'neutral')",
            name="strategy_profile_diagnostics_label_allowed",
        ),
        Index(
            "ix_strategy_profile_diagnostics_workspace_profile_horizon",
            "workspace_id",
            "strategy_profile_key",
            "horizon_minutes",
        ),
        Index("ix_strategy_profile_diagnostics_diagnostic_run_id", "diagnostic_run_id"),
        Index("ix_strategy_profile_diagnostics_diagnostic_label", "diagnostic_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    diagnostic_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profile_diagnostic_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    strategy_profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    strategy_profile_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
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
    average_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    average_max_favorable_move: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10), nullable=True
    )
    average_max_adverse_move: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_net_move: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_max_favorable_pips: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10), nullable=True
    )
    average_max_adverse_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_net_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    average_max_favorable_ticks: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10), nullable=True
    )
    average_max_adverse_ticks: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 10), nullable=True
    )
    average_net_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    confidence_alignment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    diagnostic_label: Mapped[str] = mapped_column(String(40), nullable=False)
    diagnostic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class PatternOutcomeDiagnostic(Base):
    __tablename__ = "pattern_outcome_diagnostics"
    __table_args__ = (
        CheckConstraint("horizon_minutes > 0", name="pattern_outcome_diagnostics_horizon_positive"),
        CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0",
            name="pattern_outcome_diagnostics_counts_non_negative",
        ),
        CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="pattern_outcome_diagnostics_rates_range",
        ),
        CheckConstraint(
            "confidence_alignment_score is null or "
            "(confidence_alignment_score >= 0 and confidence_alignment_score <= 1)",
            name="pattern_outcome_diagnostics_confidence_alignment_range",
        ),
        CheckConstraint(
            "diagnostic_label in ('strong_follow_through', 'mixed_behavior', 'reversal_prone', "
            "'low_sample', 'insufficient_data', 'needs_threshold_review', 'neutral')",
            name="pattern_outcome_diagnostics_label_allowed",
        ),
        Index(
            "ix_pattern_outcome_diagnostics_workspace_pattern_horizon",
            "workspace_id",
            "pattern_type",
            "horizon_minutes",
        ),
        Index("ix_pattern_outcome_diagnostics_diagnostic_run_id", "diagnostic_run_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    diagnostic_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profile_diagnostic_runs.id", ondelete="CASCADE"),
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
    horizon_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_count: Mapped[int] = mapped_column(Integer, nullable=False)
    continuation_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    reversal_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    no_follow_through_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    average_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    confidence_alignment_score: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    diagnostic_label: Mapped[str] = mapped_column(String(40), nullable=False)
    diagnostic_summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class CalibrationRecommendation(Base):
    __tablename__ = "calibration_recommendations"
    __table_args__ = (
        CheckConstraint(
            "recommendation_type in ('review_minimum_confidence', 'review_candidate_strength', "
            "'tighten_profile_filter', 'loosen_profile_filter', 'review_pattern_detector', "
            "'increase_sample_size', 'monitor_symbol_timeframe', 'no_change')",
            name="calibration_recommendations_type_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="calibration_recommendations_severity_allowed",
        ),
        CheckConstraint(
            "status in ('open', 'acknowledged', 'dismissed', 'applied_manually')",
            name="calibration_recommendations_status_allowed",
        ),
        CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="calibration_recommendations_horizon_positive",
        ),
        Index(
            "ix_calibration_recommendations_workspace_status_severity",
            "workspace_id",
            "status",
            "severity",
        ),
        Index(
            "ix_calibration_recommendations_strategy_profile_status",
            "strategy_profile_key",
            "status",
        ),
        Index("ix_calibration_recommendations_diagnostic_run_id", "diagnostic_run_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    diagnostic_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profile_diagnostic_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommendation_type: Mapped[str] = mapped_column(String(48), nullable=False)
    strategy_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    strategy_profile_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    horizon_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_change_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    evidence_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
