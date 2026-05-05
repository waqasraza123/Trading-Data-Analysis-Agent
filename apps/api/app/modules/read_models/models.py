from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DashboardSymbolReadModel(Base):
    __tablename__ = "dashboard_symbol_read_models"
    __table_args__ = (
        CheckConstraint(
            "pending_action_count >= 0 and warning_count >= 0",
            name="dashboard_symbol_read_models_counts_non_negative",
        ),
        Index(
            "uq_dashboard_symbol_read_models_identity",
            "workspace_id",
            "symbol_id",
            "source_id",
            "timeframe",
            "read_model_version",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_dashboard_symbol_read_models_workspace_timeframe", "workspace_id", "timeframe"),
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
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    read_model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    latest_final_candle_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    freshness_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_quality_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latest_signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_bias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latest_pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_confidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latest_priority_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    latest_priority_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    setup_quality_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market_regime_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_session_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pending_action_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    warning_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    updated_at = updated_at_column()
    created_at = created_at_column()


class SignalCardReadModel(Base):
    __tablename__ = "signal_card_read_models"
    __table_args__ = (
        CheckConstraint(
            "confidence_score is null or (confidence_score >= 0 and confidence_score <= 1)",
            name="signal_card_read_models_confidence_score_range",
        ),
        CheckConstraint(
            "priority_score is null or (priority_score >= 0 and priority_score <= 1)",
            name="signal_card_read_models_priority_score_range",
        ),
        Index(
            "uq_signal_card_read_models_signal_version",
            "signal_id",
            "read_model_version",
            unique=True,
        ),
        Index(
            "ix_signal_card_read_models_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index(
            "ix_signal_card_read_models_workspace_review_bucket", "workspace_id", "review_bucket"
        ),
        Index(
            "ix_signal_card_read_models_workspace_priority_label", "workspace_id", "priority_label"
        ),
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
    read_model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    classification_status: Mapped[str] = mapped_column(String(32), nullable=False)
    bias: Mapped[str] = mapped_column(String(32), nullable=False)
    pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    priority_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    priority_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    review_bucket: Mapped[str | None] = mapped_column(String(48), nullable=True)
    setup_quality_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    freshness_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_quality_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    readiness_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    outcome_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    evidence_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    risk_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    action_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    warning_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    searchable_text: Mapped[str] = mapped_column(String(4000), nullable=False)
    updated_at = updated_at_column()
    created_at = created_at_column()


class CommandCenterReadModel(Base):
    __tablename__ = "command_center_read_models"
    __table_args__ = (
        CheckConstraint(
            "warning_count >= 0", name="command_center_read_models_warning_count_non_negative"
        ),
        Index("ix_command_center_read_models_workspace_generated", "workspace_id", "generated_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    read_model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    sections_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    warning_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()
