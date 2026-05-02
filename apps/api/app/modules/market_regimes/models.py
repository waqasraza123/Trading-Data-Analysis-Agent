from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class TrendRegime(StrEnum):
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    MIXED = "mixed"
    UNCLEAR = "unclear"


class VolatilityRegime(StrEnum):
    COMPRESSED = "compressed"
    NORMAL = "normal"
    EXPANDING = "expanding"
    HIGH_VOLATILITY = "high_volatility"
    SPIKE = "spike"
    UNCLEAR = "unclear"


class RangeRegime(StrEnum):
    INSIDE_RANGE = "inside_range"
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    FAKEOUT_RISK = "fakeout_risk"
    RANGE_RETEST = "range_retest"
    UNCLEAR = "unclear"


class DataQualityLabel(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    DEGRADED = "degraded"
    INSUFFICIENT = "insufficient"


class RegimeConfidenceLabel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class MarketRegimeContext(Base):
    __tablename__ = "market_regime_contexts"
    __table_args__ = (
        CheckConstraint(
            "trend_regime in ('uptrend', 'downtrend', 'sideways', 'mixed', 'unclear')",
            name="market_regime_trend_allowed",
        ),
        CheckConstraint(
            "volatility_regime in "
            "('compressed', 'normal', 'expanding', 'high_volatility', 'spike', 'unclear')",
            name="market_regime_volatility_allowed",
        ),
        CheckConstraint(
            "range_regime in "
            "('inside_range', 'breakout', 'breakdown', 'fakeout_risk', 'range_retest', 'unclear')",
            name="market_regime_range_allowed",
        ),
        CheckConstraint(
            "data_quality_label in ('strong', 'acceptable', 'degraded', 'insufficient')",
            name="market_regime_data_quality_allowed",
        ),
        CheckConstraint(
            "confidence_score >= 0 and confidence_score <= 1",
            name="market_regime_confidence_score_range",
        ),
        CheckConstraint(
            "confidence_label in ('low', 'medium', 'high', 'very_high')",
            name="market_regime_confidence_label_allowed",
        ),
        UniqueConstraint(
            "analysis_run_id",
            "regime_version",
            name="uq_market_regime_contexts_analysis_run_version",
        ),
        Index(
            "ix_market_regime_contexts_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index("ix_market_regime_contexts_analysis_run_id", "analysis_run_id"),
        Index("ix_market_regime_contexts_signal_id", "signal_id"),
        Index("ix_market_regime_contexts_trend_regime", "trend_regime"),
        Index("ix_market_regime_contexts_volatility_regime", "volatility_regime"),
        Index("ix_market_regime_contexts_range_regime", "range_regime"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
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
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    regime_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trend_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    volatility_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    range_regime: Mapped[str] = mapped_column(String(32), nullable=False)
    liquidity_regime: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_label: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(String(1000), nullable=False)
    feature_inputs_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    indicator_inputs_json: Mapped[dict[str, object]] = mapped_column(
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
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
