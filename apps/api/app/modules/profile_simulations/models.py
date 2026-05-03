from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class StrategyProfileSimulationRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class StrategyProfileSimulationDecisionChangeType(StrEnum):
    UNCHANGED = "unchanged"
    INCLUDED = "included"
    EXCLUDED = "excluded"
    BIAS_CHANGED = "bias_changed"
    PATTERN_CHANGED = "pattern_changed"
    CONFIDENCE_CHANGED = "confidence_changed"
    NO_CANDIDATE = "no_candidate"


class StrategyProfileSimulationRun(Base):
    __tablename__ = "strategy_profile_simulation_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="strategy_profile_simulation_runs_status_allowed",
        ),
        CheckConstraint(
            "sampled_signal_count >= 0 and included_count >= 0 and excluded_count >= 0 "
            "and changed_decision_count >= 0",
            name="strategy_profile_simulation_runs_counts_non_negative",
        ),
        Index(
            "ix_strategy_profile_simulation_runs_workspace_profile",
            "workspace_id",
            "base_strategy_profile_key",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    base_strategy_profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    base_strategy_profile_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    simulation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    proposed_config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    horizons_json: Mapped[list[int]] = mapped_column(JSONB, nullable=False)
    sampled_signal_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    included_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    excluded_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    changed_decision_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class StrategyProfileSimulationResult(Base):
    __tablename__ = "strategy_profile_simulation_results"
    __table_args__ = (
        CheckConstraint(
            "decision_change_type in ('unchanged', 'included', 'excluded', 'bias_changed', "
            "'pattern_changed', 'confidence_changed', 'no_candidate')",
            name="strategy_profile_simulation_results_decision_change_type_allowed",
        ),
        CheckConstraint(
            "original_confidence_score is null or "
            "(original_confidence_score >= 0 and original_confidence_score <= 1)",
            name="strategy_profile_simulation_results_original_confidence_range",
        ),
        CheckConstraint(
            "simulated_confidence_score is null or "
            "(simulated_confidence_score >= 0 and simulated_confidence_score <= 1)",
            name="strategy_profile_simulation_results_simulated_confidence_range",
        ),
        CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="strategy_profile_simulation_results_horizon_positive",
        ),
        Index(
            "ix_strategy_profile_simulation_results_run_id",
            "simulation_run_id",
        ),
        Index("ix_strategy_profile_simulation_results_signal_id", "signal_id"),
        Index(
            "ix_strategy_profile_simulation_results_decision_change_type",
            "decision_change_type",
        ),
        Index("ix_strategy_profile_simulation_results_outcome_label", "outcome_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    simulation_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profile_simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    original_classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    original_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    original_pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    simulated_classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    simulated_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    simulated_pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    simulated_confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    decision_change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    horizon_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
