from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DataQualityRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class DataQualityScopeType(StrEnum):
    CANDLE_RANGE = "candle_range"
    DATA_SOURCE = "data_source"
    LIVE_SUBSCRIPTION = "live_subscription"


class DataQualityLabel(StrEnum):
    STRONG = "strong"
    ACCEPTABLE = "acceptable"
    DEGRADED = "degraded"
    POOR = "poor"
    INSUFFICIENT_DATA = "insufficient_data"


class DataQualityFindingSeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DataQualityRun(Base):
    __tablename__ = "data_quality_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="data_quality_runs_status_allowed",
        ),
        CheckConstraint(
            "scope_type in ('candle_range', 'data_source', 'live_subscription')",
            name="data_quality_runs_scope_type_allowed",
        ),
        CheckConstraint(
            "quality_label in ('strong', 'acceptable', 'degraded', 'poor', 'insufficient_data')",
            name="data_quality_runs_quality_label_allowed",
        ),
        CheckConstraint(
            "quality_score >= 0 and quality_score <= 1",
            name="data_quality_runs_quality_score_range",
        ),
        CheckConstraint(
            "candle_count >= 0 and finding_count >= 0",
            name="data_quality_runs_counts_non_negative",
        ),
        Index("ix_data_quality_runs_workspace_scope", "workspace_id", "scope_type"),
        Index("ix_data_quality_runs_quality_label", "quality_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_version: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    live_subscription_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("live_feed_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candle_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    finding_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quality_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    quality_label: Mapped[str] = mapped_column(String(32), nullable=False)
    summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class DataQualityFinding(Base):
    __tablename__ = "data_quality_findings"
    __table_args__ = (
        CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="data_quality_findings_severity_allowed",
        ),
        Index("ix_data_quality_findings_run_id", "data_quality_run_id"),
        Index("ix_data_quality_findings_workspace_severity", "workspace_id", "severity"),
        Index("ix_data_quality_findings_finding_type", "finding_type"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    data_quality_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_quality_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
