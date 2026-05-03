from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class EventStudyRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class EventStudyVolatilityReaction(StrEnum):
    NONE = "none"
    NORMAL = "normal"
    ELEVATED = "elevated"
    SPIKE = "spike"
    INSUFFICIENT_DATA = "insufficient_data"


class EventStudyDirectionLabel(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    INSUFFICIENT_DATA = "insufficient_data"


class EventStudyReactionLabel(StrEnum):
    STRONG_REACTION = "strong_reaction"
    MODERATE_REACTION = "moderate_reaction"
    WEAK_REACTION = "weak_reaction"
    NO_CLEAR_REACTION = "no_clear_reaction"
    INSUFFICIENT_DATA = "insufficient_data"


class EventStudyDataQualityLabel(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT_DATA = "insufficient_data"


class EventStudyRun(Base):
    __tablename__ = "event_study_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="event_study_runs_status_allowed",
        ),
        CheckConstraint("pre_event_minutes >= 0", name="event_study_runs_pre_minutes_non_negative"),
        CheckConstraint("post_event_minutes > 0", name="event_study_runs_post_minutes_positive"),
        CheckConstraint(
            "analyzed_symbol_count >= 0",
            name="event_study_runs_analyzed_symbol_count_non_negative",
        ),
        CheckConstraint("result_count >= 0", name="event_study_runs_result_count_non_negative"),
        Index("ix_event_study_runs_workspace_news_event", "workspace_id", "news_event_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    news_event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    event_study_version: Mapped[str] = mapped_column(String(32), nullable=False)
    pre_event_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    post_event_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    symbol_filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    analyzed_symbol_count: Mapped[int] = mapped_column(
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
    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class EventStudyResult(Base):
    __tablename__ = "event_study_results"
    __table_args__ = (
        CheckConstraint(
            "volatility_reaction in ('none', 'normal', 'elevated', 'spike', 'insufficient_data')",
            name="event_study_results_volatility_reaction_allowed",
        ),
        CheckConstraint(
            "direction_label in ('bullish', 'bearish', 'neutral', 'mixed', 'insufficient_data')",
            name="event_study_results_direction_label_allowed",
        ),
        CheckConstraint(
            "reaction_label in ('strong_reaction', 'moderate_reaction', 'weak_reaction', "
            "'no_clear_reaction', 'insufficient_data')",
            name="event_study_results_reaction_label_allowed",
        ),
        CheckConstraint(
            "data_quality_label in ('complete', 'partial', 'insufficient_data')",
            name="event_study_results_data_quality_label_allowed",
        ),
        CheckConstraint("pre_candle_count >= 0", name="event_study_results_pre_count_non_negative"),
        CheckConstraint("post_candle_count >= 0", name="event_study_results_post_count_non_negative"),
        Index(
            "ix_event_study_results_news_symbol_timeframe",
            "news_event_id",
            "symbol_id",
            "timeframe",
        ),
        Index("ix_event_study_results_reaction_label", "reaction_label"),
        Index("ix_event_study_results_run_id", "event_study_run_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_study_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("event_study_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    news_event_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("news_events.id", ondelete="CASCADE"),
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
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pre_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pre_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    post_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    post_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pre_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    post_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    pre_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    post_move: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    post_move_pips: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    post_move_ticks: Mapped[Decimal | None] = mapped_column(Numeric(24, 10), nullable=True)
    pre_volatility_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    post_volatility_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    volatility_reaction: Mapped[str] = mapped_column(String(32), nullable=False)
    direction_label: Mapped[str] = mapped_column(String(32), nullable=False)
    reaction_label: Mapped[str] = mapped_column(String(32), nullable=False)
    data_quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
