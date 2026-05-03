from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ExplanationComparisonRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ExplanationAlignmentLabel(StrEnum):
    ALIGNED = "aligned"
    MOSTLY_ALIGNED = "mostly_aligned"
    MIXED = "mixed"
    CONFLICTING = "conflicting"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class ExplanationComparisonFindingType(StrEnum):
    MISSING_CONTEXT = "missing_context"
    CONTRADICTION = "contradiction"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    OMITTED_RISK = "omitted_risk"
    UNSAFE_LANGUAGE = "unsafe_language"
    CAUSATION_LANGUAGE = "causation_language"
    EXPLANATION_MISMATCH = "explanation_mismatch"


class ExplanationComparisonSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExplanationComparisonRun(Base):
    __tablename__ = "explanation_comparison_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="explanation_comparison_runs_status_allowed",
        ),
        CheckConstraint(
            "alignment_label in ('aligned', 'mostly_aligned', 'mixed', 'conflicting', "
            "'insufficient_context')",
            name="explanation_comparison_runs_alignment_label_allowed",
        ),
        CheckConstraint(
            "alignment_score >= 0 and alignment_score <= 1",
            name="explanation_comparison_runs_score_range",
        ),
        Index("ix_explanation_comparison_runs_workspace_signal", "workspace_id", "signal_id"),
        Index("ix_explanation_comparison_runs_alignment_label", "alignment_label"),
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
    comparison_version: Mapped[str] = mapped_column(String(40), nullable=False)
    deterministic_explanation_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("deterministic_explanations.id", ondelete="SET NULL"),
        nullable=True,
    )
    llm_explanation_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_explanations.id", ondelete="SET NULL"),
        nullable=True,
    )
    reasoning_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    alignment_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    alignment_label: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class ExplanationComparisonFinding(Base):
    __tablename__ = "explanation_comparison_findings"
    __table_args__ = (
        CheckConstraint(
            "finding_type in ('missing_context', 'contradiction', 'unsupported_claim', "
            "'omitted_risk', 'unsafe_language', 'causation_language', "
            "'explanation_mismatch')",
            name="explanation_comparison_findings_type_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="explanation_comparison_findings_severity_allowed",
        ),
        Index("ix_explanation_comparison_findings_run_id", "comparison_run_id"),
        Index(
            "ix_explanation_comparison_findings_severity_code",
            "severity",
            "code",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    comparison_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("explanation_comparison_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
