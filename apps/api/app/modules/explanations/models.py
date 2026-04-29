from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
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


class ExplanationType(StrEnum):
    DETERMINISTIC_SIGNAL = "deterministic_signal"
    DETERMINISTIC_NO_SIGNAL = "deterministic_no_signal"


class ExplanationSafetyStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FALLBACK_USED = "fallback_used"


class DeterministicExplanation(Base):
    __tablename__ = "deterministic_explanations"
    __table_args__ = (
        CheckConstraint(
            "explanation_type in ('deterministic_signal', 'deterministic_no_signal')",
            name="deterministic_explanation_type_allowed",
        ),
        CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used')",
            name="deterministic_explanation_safety_status_allowed",
        ),
        UniqueConstraint("signal_id", name="uq_deterministic_explanations_signal_id"),
        Index("ix_deterministic_explanations_signal_id", "signal_id"),
        Index("ix_deterministic_explanations_analysis_run_id", "analysis_run_id"),
        Index("ix_deterministic_explanations_workspace_created", "workspace_id", "created_at"),
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
    template_version: Mapped[str] = mapped_column(String(40), nullable=False)
    explanation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    short_summary: Mapped[str] = mapped_column(Text, nullable=False)
    market_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_summary: Mapped[str] = mapped_column(Text, nullable=False)
    no_signal_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_snapshot_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    safety_status: Mapped[str] = mapped_column(String(32), nullable=False)
    blocked_terms_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
