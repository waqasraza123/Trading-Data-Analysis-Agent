from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class CandleAggregationRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class TimeframeAlignment(StrEnum):
    ALIGNED = "aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    CONFLICTING = "conflicting"
    UNCLEAR = "unclear"


class TimeframeAgreementLabel(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    MIXED = "mixed"
    CONFLICTING = "conflicting"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class CandleAggregationRun(Base):
    __tablename__ = "candle_aggregation_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="candle_aggregation_run_status_allowed",
        ),
        CheckConstraint(
            "expected_base_candle_count >= 0", name="expected_base_candle_count_non_negative"
        ),
        CheckConstraint(
            "available_base_candle_count >= 0", name="available_base_candle_count_non_negative"
        ),
        CheckConstraint("produced_candle_count >= 0", name="produced_candle_count_non_negative"),
        CheckConstraint("skipped_candle_count >= 0", name="skipped_candle_count_non_negative"),
        CheckConstraint(
            "incomplete_window_count >= 0", name="incomplete_window_count_non_negative"
        ),
        Index(
            "ix_candle_aggregation_runs_workspace_symbol_timeframes",
            "workspace_id",
            "symbol_id",
            "base_timeframe",
            "target_timeframe",
        ),
        Index("ix_candle_aggregation_runs_status_created", "status", "created_at"),
    )

    id = uuid_primary_key()
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
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    base_timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    target_timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_base_candle_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    available_base_candle_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    produced_candle_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    skipped_candle_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    incomplete_window_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    aggregation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class DerivedCandleLineage(Base):
    __tablename__ = "derived_candle_lineage"
    __table_args__ = (
        CheckConstraint(
            "expected_base_count >= 0", name="derived_expected_base_count_non_negative"
        ),
        CheckConstraint("actual_base_count >= 0", name="derived_actual_base_count_non_negative"),
        CheckConstraint(
            "completeness_score >= 0 and completeness_score <= 1",
            name="derived_completeness_score_range",
        ),
        Index("ix_derived_candle_lineage_derived_candle_id", "derived_candle_id"),
        Index(
            "ix_derived_candle_lineage_workspace_symbol_target_timestamp",
            "workspace_id",
            "symbol_id",
            "target_timeframe",
            "derived_timestamp",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    aggregation_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("candle_aggregation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    derived_candle_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("candles.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    base_timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    target_timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    derived_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_base_count: Mapped[int] = mapped_column(Integer, nullable=False)
    actual_base_count: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()


class MultiTimeframeContext(Base):
    __tablename__ = "multi_timeframe_contexts"
    __table_args__ = (
        CheckConstraint(
            "trend_alignment in ('aligned', 'partially_aligned', 'conflicting', 'unclear')",
            name="multi_timeframe_trend_alignment_allowed",
        ),
        CheckConstraint(
            "volatility_alignment in ('aligned', 'partially_aligned', 'conflicting', 'unclear')",
            name="multi_timeframe_volatility_alignment_allowed",
        ),
        CheckConstraint(
            "range_alignment in ('aligned', 'partially_aligned', 'conflicting', 'unclear')",
            name="multi_timeframe_range_alignment_allowed",
        ),
        CheckConstraint(
            "agreement_score >= 0 and agreement_score <= 1",
            name="multi_timeframe_agreement_score_range",
        ),
        CheckConstraint(
            "agreement_label in ('strong', 'acceptable', 'mixed', 'conflicting', "
            "'insufficient_context')",
            name="multi_timeframe_agreement_label_allowed",
        ),
        Index("ix_multi_timeframe_contexts_analysis_run_id", "analysis_run_id"),
        Index("ix_multi_timeframe_contexts_signal_id", "signal_id"),
        Index(
            "ix_multi_timeframe_contexts_workspace_symbol_primary",
            "workspace_id",
            "symbol_id",
            "primary_timeframe",
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
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    primary_timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    context_timeframes_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    context_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trend_alignment: Mapped[str] = mapped_column(String(32), nullable=False)
    volatility_alignment: Mapped[str] = mapped_column(String(32), nullable=False)
    range_alignment: Mapped[str] = mapped_column(String(32), nullable=False)
    agreement_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    agreement_label: Mapped[str] = mapped_column(String(32), nullable=False)
    context_summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    context_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    warnings_json: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()
