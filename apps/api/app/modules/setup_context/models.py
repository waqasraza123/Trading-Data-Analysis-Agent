from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class SetupContextStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    FAILED = "failed"


class SetupContextDirectionalBias(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"


class SetupQualityLabel(StrEnum):
    STRONG_CONTEXT = "strong_context"
    ACCEPTABLE_CONTEXT = "acceptable_context"
    MIXED_CONTEXT = "mixed_context"
    REVIEW_REQUIRED = "review_required"
    AVOID_CONDITION = "avoid_condition"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class SetupContext(Base):
    __tablename__ = "setup_contexts"
    __table_args__ = (
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'insufficient_context', 'failed')",
            name="setup_contexts_status_allowed",
        ),
        CheckConstraint(
            "directional_bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="setup_contexts_directional_bias_allowed",
        ),
        CheckConstraint(
            "setup_quality_label in ('strong_context', 'acceptable_context', 'mixed_context', "
            "'review_required', 'avoid_condition', 'insufficient_context')",
            name="setup_contexts_quality_label_allowed",
        ),
        CheckConstraint(
            "setup_quality_score >= 0 and setup_quality_score <= 1",
            name="setup_contexts_quality_score_range",
        ),
        UniqueConstraint("signal_id", "context_version", name="uq_setup_contexts_signal_version"),
        Index(
            "ix_setup_contexts_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index("ix_setup_contexts_signal_id", "signal_id"),
        Index("ix_setup_contexts_analysis_run_id", "analysis_run_id"),
        Index("ix_setup_contexts_directional_bias", "directional_bias"),
        Index("ix_setup_contexts_quality_label", "setup_quality_label"),
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
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    context_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    directional_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    setup_quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    setup_quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    invalidation_context_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    observation_zones_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    target_context_zones_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    wait_conditions_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    avoid_reasons_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    timeframe_agreement_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    data_quality_warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    risk_notes_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    next_observations_json: Mapped[list[dict[str, object]]] = mapped_column(
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
