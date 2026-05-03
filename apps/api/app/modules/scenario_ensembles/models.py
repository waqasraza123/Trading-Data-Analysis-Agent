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


class ScenarioEnsembleRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"


class ScenarioConsensusLabel(StrEnum):
    STRONG_AGREEMENT = "strong_agreement"
    PARTIAL_AGREEMENT = "partial_agreement"
    DISAGREEMENT = "disagreement"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    FAILED = "failed"


class ScenarioEnsembleItemStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"


class ScenarioEnsembleRun(Base):
    __tablename__ = "scenario_ensemble_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed', "
            "'provider_not_configured')",
            name="scenario_ensemble_runs_status_allowed",
        ),
        CheckConstraint(
            "consensus_label in ('strong_agreement', 'partial_agreement', 'disagreement', "
            "'insufficient_context', 'failed')",
            name="scenario_ensemble_runs_consensus_label_allowed",
        ),
        CheckConstraint(
            "consensus_score >= 0 and consensus_score <= 1",
            name="scenario_ensemble_runs_consensus_score_range",
        ),
        Index("ix_scenario_ensemble_runs_workspace_signal", "workspace_id", "signal_id"),
        Index("ix_scenario_ensemble_runs_consensus_label", "consensus_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ensemble_version: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_providers_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    requested_models_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    reasoning_run_ids_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    consensus_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    consensus_label: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    grounding_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ScenarioEnsembleItem(Base):
    __tablename__ = "scenario_ensemble_items"
    __table_args__ = (
        CheckConstraint(
            "status in ('completed', 'failed', 'blocked', 'fallback_used', "
            "'provider_not_configured')",
            name="scenario_ensemble_items_status_allowed",
        ),
        Index("ix_scenario_ensemble_items_run_id", "ensemble_run_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    ensemble_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scenario_ensemble_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    reasoning_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scenario_types_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    suggested_actions_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    grounding_status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class ScenarioConsensusResult(Base):
    __tablename__ = "scenario_consensus_results"
    __table_args__ = (
        CheckConstraint(
            "consensus_label in ('strong_agreement', 'partial_agreement', 'disagreement', "
            "'insufficient_context', 'failed')",
            name="scenario_consensus_results_consensus_label_allowed",
        ),
        CheckConstraint(
            "agreement_count >= 0 and disagreement_count >= 0",
            name="scenario_consensus_results_counts_non_negative",
        ),
        Index("ix_scenario_consensus_results_run_id", "ensemble_run_id"),
        Index("ix_scenario_consensus_results_scenario_type", "scenario_type"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    ensemble_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("scenario_ensemble_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_type: Mapped[str] = mapped_column(String(40), nullable=False)
    agreement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    disagreement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    possibility_labels_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    supporting_evidence_json: Mapped[list[str]] = mapped_column(
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
    consensus_label: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
