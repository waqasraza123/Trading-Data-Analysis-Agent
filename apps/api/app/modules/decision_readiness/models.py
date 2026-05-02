from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
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


class DecisionReadinessSourceType(StrEnum):
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    OUTCOME = "outcome"
    SCREENSHOT_DECISION = "screenshot_decision"


class DecisionReadinessLabel(StrEnum):
    READY = "ready"
    REVIEW_RECOMMENDED = "review_recommended"
    BLOCKED = "blocked"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class DecisionReadinessStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionReadinessAssessment(Base):
    __tablename__ = "decision_readiness_assessments"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', 'screenshot_decision')",
            name="decision_readiness_source_type_allowed",
        ),
        CheckConstraint(
            "readiness_label in ('ready', 'review_recommended', 'blocked', 'insufficient_context')",
            name="decision_readiness_label_allowed",
        ),
        CheckConstraint(
            "status in ('completed', 'failed')",
            name="decision_readiness_status_allowed",
        ),
        CheckConstraint(
            "readiness_score >= 0 and readiness_score <= 1",
            name="decision_readiness_score_range",
        ),
        UniqueConstraint(
            "source_type",
            "source_id",
            "assessment_version",
            name="uq_decision_readiness_source_version",
        ),
        Index("ix_decision_readiness_workspace_label", "workspace_id", "readiness_label"),
        Index("ix_decision_readiness_signal_id", "signal_id"),
        Index("ix_decision_readiness_analysis_run_id", "analysis_run_id"),
        Index("ix_decision_readiness_source", "source_type", "source_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
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
    assessment_version: Mapped[str] = mapped_column(String(40), nullable=False)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    readiness_label: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    required_checks_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    optional_checks_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    blockers_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    next_steps_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
