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


class LlmExplanationSafetyStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"
    FAILED = "failed"


class LlmExplanationGroundingStatus(StrEnum):
    GROUNDED = "grounded"
    QUESTIONABLE = "questionable"
    FAILED = "failed"
    NOT_CHECKED = "not_checked"


class LlmExplanation(Base):
    __tablename__ = "llm_explanations"
    __table_args__ = (
        CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used', 'failed')",
            name="llm_explanation_safety_status_allowed",
        ),
        CheckConstraint(
            "grounding_status in ('grounded', 'questionable', 'failed', 'not_checked')",
            name="llm_explanation_grounding_status_allowed",
        ),
        UniqueConstraint(
            "signal_id",
            "provider",
            "model",
            "prompt_version",
            name="uq_llm_explanations_signal_id_provider_model_prompt_version",
        ),
        Index("ix_llm_explanations_signal_id", "signal_id"),
        Index("ix_llm_explanations_analysis_run_id", "analysis_run_id"),
        Index("ix_llm_explanations_workspace_created", "workspace_id", "created_at"),
    )

    id = uuid_primary_key()
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
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(80), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_text: Mapped[str] = mapped_column(Text, nullable=False)
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    blocked_terms_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    grounding_status: Mapped[str] = mapped_column(String(20), nullable=False)
    grounding_issues_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 6), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
