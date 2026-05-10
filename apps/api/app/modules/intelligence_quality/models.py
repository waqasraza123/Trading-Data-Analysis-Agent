from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class IntelligenceQualitySourceType(StrEnum):
    ANALYSIS_RUN = "analysis_run"
    SIGNAL = "signal"
    REPLAY = "replay"
    SCREENSHOT_DECISION = "screenshot_decision"


class IntelligenceQualityRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class IntelligenceQualityLabel(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    REVIEW_RECOMMENDED = "review_recommended"
    INCONSISTENT = "inconsistent"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class IntelligenceQualityFindingType(StrEnum):
    INVARIANT_FAILURE = "invariant_failure"
    CONTRADICTION = "contradiction"
    MISSING_ARTIFACT = "missing_artifact"
    DEGRADED_CONFIDENCE = "degraded_confidence"
    GROUNDING_ISSUE = "grounding_issue"
    SHADOW_DISAGREEMENT = "shadow_disagreement"
    SAFETY_ISSUE = "safety_issue"
    REVIEW_RECOMMENDATION = "review_recommendation"


class IntelligenceQualitySeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ShadowAgreement(StrEnum):
    AGREED = "agreed"
    DISAGREED_BIAS = "disagreed_bias"
    DISAGREED_PATTERN = "disagreed_pattern"
    DISAGREED_STATUS = "disagreed_status"
    NO_CANDIDATE = "no_candidate"
    NOT_APPLICABLE = "not_applicable"


class IntelligenceQualityRun(Base):
    __tablename__ = "intelligence_quality_runs"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('analysis_run', 'signal', 'replay', 'screenshot_decision')",
            name="intelligence_quality_runs_source_type_allowed",
        ),
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="intelligence_quality_runs_status_allowed",
        ),
        CheckConstraint(
            "quality_label in ('strong', 'acceptable', 'review_recommended', "
            "'inconsistent', 'insufficient_context')",
            name="intelligence_quality_runs_label_allowed",
        ),
        CheckConstraint(
            "quality_score >= 0 and quality_score <= 1",
            name="intelligence_quality_runs_score_range",
        ),
        Index("ix_intelligence_quality_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_intelligence_quality_runs_signal_id", "signal_id"),
        Index("ix_intelligence_quality_runs_analysis_run_id", "analysis_run_id"),
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
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    gate_version: Mapped[str] = mapped_column(String(40), nullable=False)
    shadow_version: Mapped[str] = mapped_column(String(40), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class IntelligenceQualityFinding(Base):
    __tablename__ = "intelligence_quality_findings"
    __table_args__ = (
        CheckConstraint(
            "finding_type in ('invariant_failure', 'contradiction', 'missing_artifact', "
            "'degraded_confidence', 'grounding_issue', 'shadow_disagreement', "
            "'safety_issue', 'review_recommendation')",
            name="intelligence_quality_findings_type_allowed",
        ),
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="intelligence_quality_findings_severity_allowed",
        ),
        Index("ix_intelligence_quality_findings_run_id", "quality_run_id"),
        Index("ix_intelligence_quality_findings_severity", "severity"),
        Index("ix_intelligence_quality_findings_code", "code"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    quality_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_quality_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(32), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class ShadowClassificationResult(Base):
    __tablename__ = "shadow_classification_results"
    __table_args__ = (
        CheckConstraint(
            "classification_status in ('signal', 'no_signal', 'unclear', 'insufficient_evidence')",
            name="shadow_classification_results_status_allowed",
        ),
        CheckConstraint(
            "bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="shadow_classification_results_bias_allowed",
        ),
        CheckConstraint(
            "confidence_score is null or (confidence_score >= 0 and confidence_score <= 1)",
            name="shadow_classification_results_confidence_range",
        ),
        CheckConstraint(
            "confidence_label is null or confidence_label in ('low', 'medium', 'high', "
            "'very_high')",
            name="shadow_classification_results_confidence_label_allowed",
        ),
        CheckConstraint(
            "agreement_with_final in ('agreed', 'disagreed_bias', 'disagreed_pattern', "
            "'disagreed_status', 'no_candidate', 'not_applicable')",
            name="shadow_classification_results_agreement_allowed",
        ),
        Index("ix_shadow_classification_results_run_id", "quality_run_id"),
        Index("ix_shadow_classification_results_profile", "strategy_profile_key"),
        Index("ix_shadow_classification_results_agreement", "agreement_with_final"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    quality_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_quality_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    strategy_profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    strategy_profile_version: Mapped[str] = mapped_column(String(32), nullable=False)
    classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(16), nullable=True)
    selected_candidate_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("pattern_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    agreement_with_final: Mapped[str] = mapped_column(String(32), nullable=False)
    disagreement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
