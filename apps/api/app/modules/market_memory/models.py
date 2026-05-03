from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class MarketMemoryDataQualityLabel(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    DEGRADED = "degraded"
    POOR = "poor"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class MarketMemoryFreshnessLabel(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    DELAYED = "delayed"
    NO_DATA = "no_data"
    UNKNOWN = "unknown"


class RollingMarketStateSnapshot(Base):
    __tablename__ = "rolling_market_state_snapshots"
    __table_args__ = (
        CheckConstraint(
            "data_quality_label in "
            "('strong', 'acceptable', 'degraded', 'poor', 'insufficient', 'unknown')",
            name="rolling_market_state_data_quality_label_allowed",
        ),
        CheckConstraint(
            "freshness_label in ('fresh', 'stale', 'delayed', 'no_data', 'unknown')",
            name="rolling_market_state_freshness_label_allowed",
        ),
        Index(
            "uq_rolling_market_state_identity",
            "workspace_id",
            "symbol_id",
            "source_id",
            "timeframe",
            "state_version",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
        Index(
            "ix_rolling_market_state_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index(
            "ix_rolling_market_state_workspace_freshness",
            "workspace_id",
            "freshness_label",
        ),
        Index(
            "ix_rolling_market_state_workspace_data_quality",
            "workspace_id",
            "data_quality_label",
        ),
        Index("ix_rolling_market_state_latest_signal_id", "latest_signal_id"),
        Index("ix_rolling_market_state_latest_analysis_run_id", "latest_analysis_run_id"),
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
    state_version: Mapped[str] = mapped_column(String(32), nullable=False)
    latest_final_candle_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latest_analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_outcome_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )
    data_quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    freshness_label: Mapped[str] = mapped_column(String(32), nullable=False)
    trend_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    volatility_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    range_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_regime_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market_session_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    multi_timeframe_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cross_asset_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_signal_bias: Mapped[str | None] = mapped_column(String(32), nullable=True)
    latest_signal_pattern_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latest_signal_confidence_label: Mapped[str | None] = mapped_column(String(32), nullable=True)
    context_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
