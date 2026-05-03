from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class CandleGapRecoveryPlanStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandleGapRecoveryItemStatus(StrEnum):
    PLANNED = "planned"
    QUEUED = "queued"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandleGapRecoveryMethod(StrEnum):
    PROVIDER_POLLING = "provider_polling"
    MANUAL_IMPORT = "manual_import"
    UNAVAILABLE = "unavailable"


class CandleGapRecoveryPlan(Base):
    __tablename__ = "candle_gap_recovery_plans"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft', 'ready', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="candle_gap_recovery_plans_status_allowed",
        ),
        CheckConstraint(
            "detected_gap_count >= 0 and planned_request_count >= 0 and "
            "completed_request_count >= 0 and skipped_request_count >= 0 and "
            "failed_request_count >= 0",
            name="candle_gap_recovery_plans_counts_non_negative",
        ),
        Index(
            "ix_candle_gap_recovery_plans_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
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
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    recovery_version: Mapped[str] = mapped_column(String(40), nullable=False)
    detection_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detection_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_gap_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    planned_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    completed_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    skipped_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    failed_request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class CandleGapRecoveryItem(Base):
    __tablename__ = "candle_gap_recovery_items"
    __table_args__ = (
        CheckConstraint(
            "status in ('planned', 'queued', 'completed', 'skipped', 'failed', 'cancelled')",
            name="candle_gap_recovery_items_status_allowed",
        ),
        CheckConstraint(
            "recovery_method in ('provider_polling', 'manual_import', 'unavailable')",
            name="candle_gap_recovery_items_method_allowed",
        ),
        CheckConstraint(
            "expected_candle_count > 0",
            name="candle_gap_recovery_items_expected_count_positive",
        ),
        Index(
            "ix_candle_gap_recovery_items_plan_status",
            "recovery_plan_id",
            "status",
        ),
        Index(
            "ix_candle_gap_recovery_items_symbol_timeframe_gap_start",
            "symbol_id",
            "timeframe",
            "gap_start_time",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    recovery_plan_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("candle_gap_recovery_plans.id", ondelete="CASCADE"),
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
    gap_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gap_end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_candle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    recovery_method: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_polling_request_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_polling_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    skip_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()
