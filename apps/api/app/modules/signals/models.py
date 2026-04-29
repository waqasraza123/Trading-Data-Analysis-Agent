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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, uuid_primary_key


class SignalClassificationStatus(StrEnum):
    SIGNAL = "signal"
    NO_SIGNAL = "no_signal"
    UNCLEAR = "unclear"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class SignalBias(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"


class SignalConfidenceLabel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        CheckConstraint(
            "classification_status in ('signal', 'no_signal', 'unclear', 'insufficient_evidence')",
            name="signal_classification_status_allowed",
        ),
        CheckConstraint(
            "bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="signal_bias_allowed",
        ),
        CheckConstraint(
            "confidence_label in ('low', 'medium', 'high', 'very_high')",
            name="signal_confidence_label_allowed",
        ),
        CheckConstraint(
            "confidence_score >= 0 and confidence_score <= 1",
            name="signal_confidence_score_range",
        ),
        CheckConstraint(
            "candidate_strength is null or (candidate_strength >= 0 and candidate_strength <= 1)",
            name="signal_candidate_strength_range",
        ),
        UniqueConstraint("analysis_run_id", name="uq_signals_analysis_run_id"),
        Index("ix_signals_analysis_run_id", "analysis_run_id"),
        Index(
            "ix_signals_workspace_symbol_timeframe_created",
            "workspace_id",
            "symbol_id",
            "timeframe",
            "created_at",
        ),
    )

    id = uuid_primary_key()
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
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    strategy_profile_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    strategy_profile_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    strategy_profile_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strategy_profile_snapshot_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(16), nullable=False)
    candidate_strength: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    selected_pattern_candidate_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("pattern_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    pips_moved: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    tick_moved: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    movement_direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    movement_quality: Mapped[str | None] = mapped_column(String(64), nullable=True)
    volatility_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trend_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    range_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    no_signal_reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )


class SignalConfidenceComponent(Base):
    __tablename__ = "signal_confidence_components"
    __table_args__ = (
        CheckConstraint(
            "component_score >= 0 and component_score <= 1",
            name="signal_confidence_component_score_range",
        ),
        CheckConstraint(
            "component_weight >= 0 and component_weight <= 1",
            name="signal_confidence_component_weight_range",
        ),
        CheckConstraint(
            "weighted_score >= 0 and weighted_score <= 1",
            name="signal_confidence_component_weighted_score_range",
        ),
        Index("ix_signal_confidence_components_signal_id", "signal_id"),
    )

    id = uuid_primary_key()
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    component_name: Mapped[str] = mapped_column(String(80), nullable=False)
    component_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    component_weight: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    weighted_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at = created_at_column()


class SignalEvidence(Base):
    __tablename__ = "signal_evidence"
    __table_args__ = (Index("ix_signal_evidence_signal_id", "signal_id"),)

    id = uuid_primary_key()
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    direction: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class SignalRiskNote(Base):
    __tablename__ = "signal_risk_notes"
    __table_args__ = (
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="signal_risk_note_severity_allowed",
        ),
        Index("ix_signal_risk_notes_signal_id", "signal_id"),
    )

    id = uuid_primary_key()
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
