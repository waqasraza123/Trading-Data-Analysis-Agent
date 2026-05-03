from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class CrossAssetContextRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class CrossAssetAlignmentLabel(StrEnum):
    ALIGNED = "aligned"
    PARTIALLY_ALIGNED = "partially_aligned"
    CONFLICTING = "conflicting"
    DIVERGENT = "divergent"
    INSUFFICIENT_DATA = "insufficient_data"


class CrossAssetLeadLagLabel(StrEnum):
    BASE_LEADS = "base_leads"
    COMPARED_LEADS = "compared_leads"
    SYNCHRONOUS = "synchronous"
    NO_CLEAR_RELATIONSHIP = "no_clear_relationship"
    INSUFFICIENT_DATA = "insufficient_data"


class CrossAssetDataQualityLabel(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    DEGRADED = "degraded"
    INSUFFICIENT_DATA = "insufficient_data"


class CrossAssetContextRun(Base):
    __tablename__ = "cross_asset_context_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="cross_asset_context_runs_status_allowed",
        ),
        CheckConstraint(
            "compared_symbol_count >= 0",
            name="cross_asset_context_runs_compared_symbol_count_non_negative",
        ),
        CheckConstraint(
            "result_count >= 0",
            name="cross_asset_context_runs_result_count_non_negative",
        ),
        Index(
            "ix_cross_asset_context_runs_workspace_base_timeframe",
            "workspace_id",
            "base_symbol_id",
            "timeframe",
        ),
        Index("ix_cross_asset_context_runs_analysis_run_id", "analysis_run_id"),
        Index("ix_cross_asset_context_runs_signal_id", "signal_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=True,
    )
    base_symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    compared_symbol_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    result_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class CrossAssetContextResult(Base):
    __tablename__ = "cross_asset_context_results"
    __table_args__ = (
        CheckConstraint(
            "correlation_score >= -1 and correlation_score <= 1",
            name="cross_asset_context_results_correlation_score_range",
        ),
        CheckConstraint(
            "divergence_score >= 0 and divergence_score <= 1",
            name="cross_asset_context_results_divergence_score_range",
        ),
        CheckConstraint(
            "alignment_label in ('aligned', 'partially_aligned', 'conflicting', "
            "'divergent', 'insufficient_data')",
            name="cross_asset_context_results_alignment_label_allowed",
        ),
        CheckConstraint(
            "lead_lag_label in ('base_leads', 'compared_leads', 'synchronous', "
            "'no_clear_relationship', 'insufficient_data')",
            name="cross_asset_context_results_lead_lag_label_allowed",
        ),
        CheckConstraint(
            "data_quality_label in ('strong', 'acceptable', 'degraded', 'insufficient_data')",
            name="cross_asset_context_results_data_quality_label_allowed",
        ),
        Index("ix_cross_asset_context_results_context_run_id", "context_run_id"),
        Index(
            "ix_cross_asset_context_results_base_compared_timeframe",
            "base_symbol_id",
            "compared_symbol_id",
            "timeframe",
        ),
        Index("ix_cross_asset_context_results_alignment_label", "alignment_label"),
        Index("ix_cross_asset_context_results_lead_lag_label", "lead_lag_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    context_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("cross_asset_context_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    base_symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    compared_symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    base_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    compared_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    base_direction: Mapped[str] = mapped_column(String(32), nullable=False)
    compared_direction: Mapped[str] = mapped_column(String(32), nullable=False)
    correlation_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    alignment_label: Mapped[str] = mapped_column(String(32), nullable=False)
    lead_lag_offset_candles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_lag_label: Mapped[str] = mapped_column(String(32), nullable=False)
    divergence_score: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    data_quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
