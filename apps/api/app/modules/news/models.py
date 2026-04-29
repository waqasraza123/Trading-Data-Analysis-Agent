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


class NewsEventType(StrEnum):
    ECONOMIC_CALENDAR = "economic_calendar"
    MARKET_NEWS = "market_news"
    CRYPTO_EVENT = "crypto_event"
    EARNINGS = "earnings"
    CENTRAL_BANK = "central_bank"
    MANUAL = "manual"


class NewsImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class NewsSentiment(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class CorrelationLabel(StrEnum):
    NONE = "none"
    WEAK = "weak"
    POSSIBLE = "possible"
    STRONG = "strong"


class DirectionAlignment(StrEnum):
    ALIGNED = "aligned"
    OPPOSED = "opposed"
    NEUTRAL = "neutral"
    UNKNOWN = "unknown"


class VolatilityReaction(StrEnum):
    NONE = "none"
    NORMAL = "normal"
    ELEVATED = "elevated"
    SPIKE = "spike"
    UNKNOWN = "unknown"


class NewsEvent(Base):
    __tablename__ = "news_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('economic_calendar', 'market_news', 'crypto_event', "
            "'earnings', 'central_bank', 'manual')",
            name="news_event_type_allowed",
        ),
        CheckConstraint(
            "importance in ('low', 'medium', 'high', 'critical', 'unknown')",
            name="news_importance_allowed",
        ),
        CheckConstraint(
            "sentiment in ('bullish', 'bearish', 'neutral', 'mixed', 'unknown')",
            name="news_sentiment_allowed",
        ),
        Index("ix_news_events_workspace_time", "workspace_id", "event_time"),
        Index("ix_news_events_currency_time", "currency", "event_time"),
        Index("ix_news_events_asset_time", "asset", "event_time"),
        Index("ix_news_events_symbol_time", "symbol_id", "event_time"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    importance: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=NewsImportance.UNKNOWN.value,
        server_default=NewsImportance.UNKNOWN.value,
    )
    sentiment: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=NewsSentiment.UNKNOWN.value,
        server_default=NewsSentiment.UNKNOWN.value,
    )
    actual_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    forecast_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    previous_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    impact_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class SignalNewsCorrelation(Base):
    __tablename__ = "signal_news_correlations"
    __table_args__ = (
        CheckConstraint(
            "correlation_score >= 0 and correlation_score <= 1",
            name="signal_news_correlation_score_range",
        ),
        CheckConstraint(
            "relevance_score >= 0 and relevance_score <= 1",
            name="signal_news_relevance_score_range",
        ),
        CheckConstraint(
            "importance_score >= 0 and importance_score <= 1",
            name="signal_news_importance_score_range",
        ),
        CheckConstraint(
            "magnitude_score >= 0 and magnitude_score <= 1",
            name="signal_news_magnitude_score_range",
        ),
        CheckConstraint(
            "sentiment_score >= 0 and sentiment_score <= 1",
            name="signal_news_sentiment_score_range",
        ),
        CheckConstraint(
            "correlation_label in ('none', 'weak', 'possible', 'strong')",
            name="signal_news_correlation_label_allowed",
        ),
        CheckConstraint(
            "direction_alignment in ('aligned', 'opposed', 'neutral', 'unknown')",
            name="signal_news_direction_alignment_allowed",
        ),
        CheckConstraint(
            "volatility_reaction in ('none', 'normal', 'elevated', 'spike', 'unknown')",
            name="signal_news_volatility_reaction_allowed",
        ),
        Index("ix_signal_news_correlations_signal_id", "signal_id"),
        Index("ix_signal_news_correlations_analysis_run_id", "analysis_run_id"),
        Index("ix_signal_news_correlations_news_event_id", "news_event_id"),
        Index("ix_signal_news_correlations_label", "correlation_label"),
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
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    news_event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    correlation_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    correlation_label: Mapped[str] = mapped_column(String(16), nullable=False)
    time_delta_minutes: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    direction_alignment: Mapped[str] = mapped_column(String(16), nullable=False)
    volatility_reaction: Mapped[str] = mapped_column(String(16), nullable=False)
    relevance_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    importance_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    magnitude_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
