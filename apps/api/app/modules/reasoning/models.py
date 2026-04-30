from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ReasoningSourceType(StrEnum):
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    OUTCOME = "outcome"
    SCREENSHOT_DECISION = "screenshot_decision"
    REPLAY = "replay"


class ReasoningType(StrEnum):
    NEXT_SCENARIOS = "next_scenarios"
    OUTCOME_INTERPRETATION = "outcome_interpretation"
    EVIDENCE_REVIEW = "evidence_review"
    RISK_REVIEW = "risk_review"
    HUMAN_REVIEW_ASSIST = "human_review_assist"


class ReasoningRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"


class ReasoningSafetyStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"
    FAILED = "failed"


class ReasoningGroundingStatus(StrEnum):
    GROUNDED = "grounded"
    QUESTIONABLE = "questionable"
    FAILED = "failed"
    NOT_CHECKED = "not_checked"


class ScenarioType(StrEnum):
    CONTINUATION = "continuation"
    REVERSAL = "reversal"
    CONSOLIDATION = "consolidation"
    VOLATILITY_EXPANSION = "volatility_expansion"
    FAKEOUT_RISK = "fakeout_risk"
    EVENT_DRIVEN_VOLATILITY = "event_driven_volatility"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class ScenarioPossibilityLabel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNCERTAIN = "uncertain"


class LlmReasoningRun(Base):
    __tablename__ = "llm_reasoning_runs"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'outcome', 'screenshot_decision', 'replay')",
            name="llm_reasoning_runs_source_type_allowed",
        ),
        CheckConstraint(
            "reasoning_type in ('next_scenarios', 'outcome_interpretation', "
            "'evidence_review', 'risk_review', 'human_review_assist')",
            name="llm_reasoning_runs_reasoning_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'completed', 'failed', 'blocked', 'fallback_used', "
            "'provider_not_configured')",
            name="llm_reasoning_runs_status_allowed",
        ),
        CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used', 'failed')",
            name="llm_reasoning_runs_safety_status_allowed",
        ),
        CheckConstraint(
            "grounding_status in ('grounded', 'questionable', 'failed', 'not_checked')",
            name="llm_reasoning_runs_grounding_status_allowed",
        ),
        Index("ix_llm_reasoning_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_llm_reasoning_runs_signal_reasoning", "signal_id", "reasoning_type"),
        Index(
            "ix_llm_reasoning_runs_analysis_reasoning",
            "analysis_run_id",
            "reasoning_type",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    reasoning_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_snapshot_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    output_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    grounding_status: Mapped[str] = mapped_column(String(20), nullable=False)
    blocked_terms_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    grounding_issues_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class ScenarioHypothesis(Base):
    __tablename__ = "scenario_hypotheses"
    __table_args__ = (
        CheckConstraint(
            "scenario_type in ('continuation', 'reversal', 'consolidation', "
            "'volatility_expansion', 'fakeout_risk', 'event_driven_volatility', "
            "'insufficient_context')",
            name="scenario_hypotheses_scenario_type_allowed",
        ),
        CheckConstraint(
            "possibility_label in ('low', 'medium', 'high', 'uncertain')",
            name="scenario_hypotheses_possibility_label_allowed",
        ),
        Index("ix_scenario_hypotheses_reasoning_run_id", "reasoning_run_id"),
        Index("ix_scenario_hypotheses_signal_id", "signal_id"),
        Index("ix_scenario_hypotheses_scenario_type", "scenario_type"),
    )

    id = uuid_primary_key()
    reasoning_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    scenario_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scenario_label: Mapped[str] = mapped_column(String(300), nullable=False)
    possibility_label: Mapped[str] = mapped_column(String(16), nullable=False)
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
    outcome_history_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    next_observations_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    suggested_backend_actions_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    risk_notes_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at = created_at_column()
