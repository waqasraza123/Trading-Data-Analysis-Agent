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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ScenarioOutcomeEvaluationStatus(StrEnum):
    EVALUATED = "evaluated"
    INSUFFICIENT_OUTCOME_DATA = "insufficient_outcome_data"
    NOT_APPLICABLE = "not_applicable"
    FAILED = "failed"


class ScenarioOutcomeSupportLabel(StrEnum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    CONTRADICTED = "contradicted"
    INCONCLUSIVE = "inconclusive"
    NOT_APPLICABLE = "not_applicable"


class ScenarioOutcomeSummaryRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ScenarioHypothesisOutcome(Base):
    __tablename__ = "scenario_hypothesis_outcomes"
    __table_args__ = (
        CheckConstraint(
            "evaluation_status in ('evaluated', 'insufficient_outcome_data', "
            "'not_applicable', 'failed')",
            name="scenario_hypothesis_outcomes_evaluation_status_allowed",
        ),
        CheckConstraint(
            "support_label in ('supported', 'partially_supported', 'contradicted', "
            "'inconclusive', 'not_applicable')",
            name="scenario_hypothesis_outcomes_support_label_allowed",
        ),
        CheckConstraint(
            "support_score >= 0 and support_score <= 1",
            name="scenario_hypothesis_outcomes_support_score_range",
        ),
        CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="scenario_hypothesis_outcomes_horizon_positive",
        ),
        UniqueConstraint(
            "scenario_hypothesis_id",
            "horizon_minutes",
            "evaluation_version",
            name="uq_scenario_hypothesis_outcomes_hypothesis_horizon_version",
        ),
        Index("ix_scenario_hypothesis_outcomes_hypothesis_id", "scenario_hypothesis_id"),
        Index("ix_scenario_hypothesis_outcomes_reasoning_run_id", "reasoning_run_id"),
        Index("ix_scenario_hypothesis_outcomes_signal_id", "signal_id"),
        Index("ix_scenario_hypothesis_outcomes_scenario_type", "scenario_type"),
        Index("ix_scenario_hypothesis_outcomes_support_label", "support_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_hypothesis_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scenario_hypotheses.id", ondelete="CASCADE"),
        nullable=False,
    )
    reasoning_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    outcome_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )
    horizon_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(40), nullable=False)
    possibility_label: Mapped[str] = mapped_column(String(16), nullable=False)
    evaluation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    support_label: Mapped[str] = mapped_column(String(32), nullable=False)
    support_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    matched_outcome_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    matched_evidence_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    conflicting_evidence_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ScenarioOutcomeSummaryRun(Base):
    __tablename__ = "scenario_outcome_summary_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="scenario_outcome_summary_runs_status_allowed",
        ),
        CheckConstraint(
            "evaluated_count >= 0 and supported_count >= 0 and partially_supported_count >= 0 "
            "and contradicted_count >= 0 and inconclusive_count >= 0",
            name="scenario_outcome_summary_runs_counts_non_negative",
        ),
        Index("ix_scenario_outcome_summary_runs_workspace_created", "workspace_id", "created_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_version: Mapped[str] = mapped_column(String(32), nullable=False)
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
    supported_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    partially_supported_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    contradicted_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    inconclusive_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
