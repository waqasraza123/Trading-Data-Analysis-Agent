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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class EquityUniverseStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class EquityUniverseType(StrEnum):
    MANUAL = "manual"
    MARKET_CAP = "market_cap"
    SECTOR = "sector"
    INDEX = "index"
    WATCHLIST_LINKED = "watchlist_linked"
    CUSTOM = "custom"


class EquitySwingScanRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class EquitySwingCandidateStatus(StrEnum):
    CANDIDATE = "candidate"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFLICTED = "conflicted"
    AVOID = "avoid"
    INSUFFICIENT_DATA = "insufficient_data"
    STALE_DATA = "stale_data"


class EquitySwingSetupType(StrEnum):
    CONTINUATION = "continuation"
    MOMENTUM = "momentum"
    PULLBACK = "pullback"
    BREAKOUT_RETEST = "breakout_retest"
    REVERSAL_WATCH = "reversal_watch"
    RANGE_BREAK = "range_break"
    NO_CLEAR_SETUP = "no_clear_setup"


class EquitySwingDirectionalBias(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"


class EquitySwingSetupQualityLabel(StrEnum):
    STRONG_CONTEXT = "strong_context"
    ACCEPTABLE_CONTEXT = "acceptable_context"
    MIXED_CONTEXT = "mixed_context"
    REVIEW_REQUIRED = "review_required"
    AVOID_CONDITION = "avoid_condition"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class EquityCatalystType(StrEnum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    ANALYST_RATING = "analyst_rating"
    NEWS = "news"
    SECTOR_EVENT = "sector_event"
    MACRO_EVENT = "macro_event"
    UNUSUAL_VOLUME = "unusual_volume"
    MANUAL_NOTE = "manual_note"


class EquityCatalystImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class EquityCatalystSentiment(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class EquityUniverse(Base):
    __tablename__ = "equity_universes"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="equity_universes_status_allowed",
        ),
        CheckConstraint(
            "universe_type in ('manual', 'market_cap', 'sector', 'index', "
            "'watchlist_linked', 'custom')",
            name="equity_universes_type_allowed",
        ),
        Index("ix_equity_universes_workspace_status", "workspace_id", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    universe_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquityUniverseMember(Base):
    __tablename__ = "equity_universe_members"
    __table_args__ = (
        UniqueConstraint(
            "universe_id",
            "symbol_id",
            name="uq_equity_universe_members_universe_symbol",
        ),
        Index("ix_equity_universe_members_universe_active", "universe_id", "is_active"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    universe_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("equity_universes.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(160), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(80), nullable=True)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    average_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquitySwingScanRun(Base):
    __tablename__ = "equity_swing_scan_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="equity_swing_scan_runs_status_allowed",
        ),
        CheckConstraint("scanned_symbol_count >= 0", name="equity_scan_scanned_count_non_negative"),
        CheckConstraint("candidate_count >= 0", name="equity_scan_candidate_count_non_negative"),
        CheckConstraint("rejected_count >= 0", name="equity_scan_rejected_count_non_negative"),
        Index(
            "ix_equity_swing_scan_runs_workspace_status_created",
            "workspace_id",
            "status",
            "created_at",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    universe_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("equity_universes.id", ondelete="SET NULL"),
        nullable=True,
    )
    watchlist_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("market_watchlists.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scan_version: Mapped[str] = mapped_column(String(32), nullable=False)
    scan_profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    scanned_symbol_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    candidate_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    rejected_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EquitySwingCandidate(Base):
    __tablename__ = "equity_swing_candidates"
    __table_args__ = (
        CheckConstraint(
            "candidate_status in ('candidate', 'needs_confirmation', 'conflicted', 'avoid', "
            "'insufficient_data', 'stale_data')",
            name="equity_swing_candidates_status_allowed",
        ),
        CheckConstraint(
            "setup_type in ('continuation', 'momentum', 'pullback', 'breakout_retest', "
            "'reversal_watch', 'range_break', 'no_clear_setup')",
            name="equity_swing_candidates_setup_type_allowed",
        ),
        CheckConstraint(
            "directional_bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="equity_swing_candidates_bias_allowed",
        ),
        CheckConstraint(
            "setup_quality_label in ('strong_context', 'acceptable_context', 'mixed_context', "
            "'review_required', 'avoid_condition', 'insufficient_context')",
            name="equity_swing_candidates_quality_label_allowed",
        ),
        CheckConstraint(
            "setup_quality_score >= 0 and setup_quality_score <= 1",
            name="equity_swing_candidates_setup_quality_range",
        ),
        Index("ix_equity_swing_candidates_scan_run_id", "scan_run_id"),
        Index(
            "ix_equity_swing_candidates_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index("ix_equity_swing_candidates_quality_label", "setup_quality_label"),
        Index("ix_equity_swing_candidates_setup_type", "setup_type"),
        Index("ix_equity_swing_candidates_status", "candidate_status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("equity_swing_scan_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    candidate_status: Mapped[str] = mapped_column(String(32), nullable=False)
    setup_type: Mapped[str] = mapped_column(String(32), nullable=False)
    directional_bias: Mapped[str] = mapped_column(String(16), nullable=False)
    setup_quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    setup_quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    liquidity_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    volume_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    trend_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    pullback_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    relative_strength_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    momentum_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    volatility_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    catalyst_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    confidence_context_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    evidence_json: Mapped[list[dict[str, object]]] = mapped_column(
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
    setup_context_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("setup_contexts.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquityCatalystContext(Base):
    __tablename__ = "equity_catalyst_contexts"
    __table_args__ = (
        CheckConstraint(
            "catalyst_type in ('earnings', 'guidance', 'analyst_rating', 'news', "
            "'sector_event', 'macro_event', 'unusual_volume', 'manual_note')",
            name="equity_catalyst_contexts_type_allowed",
        ),
        CheckConstraint(
            "importance in ('low', 'medium', 'high', 'unknown')",
            name="equity_catalyst_contexts_importance_allowed",
        ),
        CheckConstraint(
            "sentiment in ('bullish', 'bearish', 'neutral', 'mixed', 'unknown')",
            name="equity_catalyst_contexts_sentiment_allowed",
        ),
        Index(
            "ix_equity_catalyst_contexts_workspace_symbol_time",
            "workspace_id",
            "symbol_id",
            "event_time",
        ),
        Index(
            "ix_equity_catalyst_contexts_type_importance",
            "catalyst_type",
            "importance",
        ),
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
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    catalyst_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(16), nullable=False)
    sentiment: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_reference_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
