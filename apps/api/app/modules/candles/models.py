from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (
        CheckConstraint("open > 0", name="open_positive"),
        CheckConstraint("high > 0", name="high_positive"),
        CheckConstraint("low > 0", name="low_positive"),
        CheckConstraint("close > 0", name="close_positive"),
        CheckConstraint("high >= open", name="high_gte_open"),
        CheckConstraint("high >= close", name="high_gte_close"),
        CheckConstraint("high >= low", name="high_gte_low"),
        CheckConstraint("low <= open", name="low_lte_open"),
        CheckConstraint("low <= close", name="low_lte_close"),
        CheckConstraint("volume is null or volume >= 0", name="volume_non_negative"),
        CheckConstraint(
            "quality_score is null or (quality_score >= 0 and quality_score <= 1)",
            name="quality_score_range",
        ),
        UniqueConstraint(
            "workspace_id",
            "symbol_id",
            "source_id",
            "timeframe",
            "timestamp",
            name="uq_candles_workspace_symbol_source_timeframe_timestamp",
        ),
        Index(
            "ix_candles_workspace_symbol_timeframe_timestamp",
            "workspace_id",
            "symbol_id",
            "timeframe",
            "timestamp",
        ),
        Index(
            "ix_candles_workspace_symbol_timeframe_timestamp_is_final",
            "workspace_id",
            "symbol_id",
            "timeframe",
            "timestamp",
            "is_final",
        ),
        Index("ix_candles_source_timestamp", "source_id", "timestamp"),
        Index("ix_candles_import_batch_id", "import_batch_id"),
        Index("ix_candles_live_feed_event_id", "live_feed_event_id"),
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
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    import_batch_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    live_feed_event_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("live_feed_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 5), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
