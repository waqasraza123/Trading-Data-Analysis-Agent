from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ProviderHealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    FAILING = "failing"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ProviderHealthFreshnessLabel(StrEnum):
    FRESH = "fresh"
    DELAYED = "delayed"
    STALE = "stale"
    NO_DATA = "no_data"
    UNKNOWN = "unknown"


class ProviderHealthSnapshot(Base):
    __tablename__ = "provider_health_snapshots"
    __table_args__ = (
        CheckConstraint(
            "status in ('healthy', 'degraded', 'stale', 'failing', 'unavailable', 'unknown')",
            name="provider_health_snapshots_status_allowed",
        ),
        CheckConstraint(
            "freshness_label in ('fresh', 'delayed', 'stale', 'no_data', 'unknown')",
            name="provider_health_snapshots_freshness_label_allowed",
        ),
        CheckConstraint(
            "consecutive_failure_count >= 0 and missing_candle_count >= 0",
            name="provider_health_snapshots_counts_non_negative",
        ),
        CheckConstraint(
            "stale_seconds is null or stale_seconds >= 0",
            name="provider_health_snapshots_stale_seconds_non_negative",
        ),
        Index(
            "ix_provider_health_snapshots_workspace_source_status",
            "workspace_id",
            "source_id",
            "status",
        ),
        Index(
            "ix_provider_health_snapshots_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index(
            "ix_provider_health_snapshots_provider_status",
            "provider",
            "status",
        ),
        Index(
            "ix_provider_health_snapshots_latest_final_candle_time",
            "latest_final_candle_time",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    freshness_label: Mapped[str] = mapped_column(String(32), nullable=False)
    latest_final_candle_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latest_successful_poll_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latest_failed_poll_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latest_gap_recovery_plan_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("candle_gap_recovery_plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_data_quality_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_quality_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    consecutive_failure_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    missing_candle_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    stale_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
