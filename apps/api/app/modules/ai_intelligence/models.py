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


class AiIntelligenceSubjectType(StrEnum):
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    OUTCOME = "outcome"
    SCREENSHOT_DECISION = "screenshot_decision"


class AiIntelligenceRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    FAILED = "failed"


class AiIntelligenceSafetyStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"
    FAILED = "failed"


class AiIntelligenceGroundingStatus(StrEnum):
    GROUNDED = "grounded"
    QUESTIONABLE = "questionable"
    FAILED = "failed"
    NOT_CHECKED = "not_checked"


class AiIntelligenceInsightType(StrEnum):
    EVIDENCE_CONSISTENCY = "evidence_consistency"
    CONFIDENCE_ALIGNMENT = "confidence_alignment"
    OUTCOME_CONTEXT = "outcome_context"
    DIAGNOSTIC_CONTEXT = "diagnostic_context"
    NEWS_CONTEXT = "news_context"
    ACTION_PLAN_CONTEXT = "action_plan_context"
    DATA_GAP = "data_gap"
    RISK_CONTEXT = "risk_context"
    HUMAN_REVIEW_CONTEXT = "human_review_context"
    GENERAL_CONTEXT = "general_context"


class AiIntelligenceSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AiIntelligenceClaimSupportStatus(StrEnum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"


class AiIntelligenceRun(Base):
    __tablename__ = "ai_intelligence_runs"
    __table_args__ = (
        CheckConstraint(
            "subject_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', "
            "'screenshot_decision')",
            name="ai_intelligence_runs_subject_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'completed', 'blocked', 'fallback_used', "
            "'provider_not_configured', 'failed')",
            name="ai_intelligence_runs_status_allowed",
        ),
        CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used', 'failed')",
            name="ai_intelligence_runs_safety_status_allowed",
        ),
        CheckConstraint(
            "grounding_status in ('grounded', 'questionable', 'failed', 'not_checked')",
            name="ai_intelligence_runs_grounding_status_allowed",
        ),
        Index("ix_ai_intelligence_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_ai_intelligence_runs_subject", "subject_type", "subject_id"),
        Index("ix_ai_intelligence_runs_signal_created", "signal_id", "created_at"),
        Index("ix_ai_intelligence_runs_analysis_created", "analysis_run_id", "created_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
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
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
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
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class AiIntelligenceInsight(Base):
    __tablename__ = "ai_intelligence_insights"
    __table_args__ = (
        CheckConstraint(
            "insight_type in ('evidence_consistency', 'confidence_alignment', "
            "'outcome_context', 'diagnostic_context', 'news_context', 'action_plan_context', "
            "'data_gap', 'risk_context', 'human_review_context', 'general_context')",
            name="ai_intelligence_insights_type_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="ai_intelligence_insights_severity_allowed",
        ),
        Index("ix_ai_intelligence_insights_run_id", "run_id"),
        Index("ix_ai_intelligence_insights_workspace_type", "workspace_id", "insight_type"),
    )

    id = uuid_primary_key()
    run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("ai_intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    insight_type: Mapped[str] = mapped_column(String(48), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_refs_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    limitations_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    safe_follow_up_actions_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at = created_at_column()


class AiIntelligenceClaim(Base):
    __tablename__ = "ai_intelligence_claims"
    __table_args__ = (
        CheckConstraint(
            "support_status in ('supported', 'partial', 'unsupported')",
            name="ai_intelligence_claims_support_status_allowed",
        ),
        Index("ix_ai_intelligence_claims_run_id", "run_id"),
        Index("ix_ai_intelligence_claims_insight_id", "insight_id"),
    )

    id = uuid_primary_key()
    run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("ai_intelligence_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    insight_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("ai_intelligence_insights.id", ondelete="CASCADE"),
        nullable=True,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    support_status: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_refs_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at = created_at_column()
