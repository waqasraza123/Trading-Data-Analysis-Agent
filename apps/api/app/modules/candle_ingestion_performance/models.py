from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class CandleIngestionPerformanceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class CandleIngestionMode(StrEnum):
    CSV_IMPORT = "csv_import"
    JSON_IMPORT = "json_import"
    PROVIDER_POLLING = "provider_polling"
    BULK_DIRECT = "bulk_direct"


class CandleIngestionConflictType(StrEnum):
    FINAL_CONFLICT = "final_conflict"
    PARTIAL_AFTER_FINAL = "partial_after_final"
    DUPLICATE_FINAL = "duplicate_final"
    INVALID_OHLC = "invalid_ohlc"
    TIMESTAMP_MISALIGNMENT = "timestamp_misalignment"


class CandleIngestionConflictResolution(StrEnum):
    SKIPPED = "skipped"
    KEPT_EXISTING = "kept_existing"
    REJECTED = "rejected"
    UPDATED_PARTIAL = "updated_partial"
    INSERTED = "inserted"


class CandleIngestionPerformanceRun(Base):
    __tablename__ = "candle_ingestion_performance_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="candle_ingestion_performance_runs_status_allowed",
        ),
        CheckConstraint(
            "ingestion_mode in ('csv_import', 'json_import', 'provider_polling', 'bulk_direct')",
            name="candle_ingestion_performance_runs_mode_allowed",
        ),
        CheckConstraint(
            "rows_received >= 0 and rows_validated >= 0 and rows_inserted >= 0 and "
            "rows_updated >= 0 and rows_skipped_duplicate >= 0 and rows_conflicted >= 0 and "
            "rows_failed >= 0 and batch_count >= 0",
            name="candle_ingestion_performance_runs_counts_non_negative",
        ),
        CheckConstraint(
            "elapsed_ms is null or elapsed_ms >= 0",
            name="candle_ingestion_performance_runs_elapsed_non_negative",
        ),
        Index(
            "ix_candle_ingestion_performance_runs_workspace_created",
            "workspace_id",
            "created_at",
        ),
        Index(
            "ix_candle_ingestion_performance_runs_import_batch_id",
            "import_batch_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    import_batch_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider_polling_request_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_polling_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    ingestion_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    rows_received: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_validated: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_inserted: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_updated: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_skipped_duplicate: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    rows_conflicted: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_failed: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    batch_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    elapsed_ms: Mapped[int | None] = mapped_column(nullable=True)
    diagnostics_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class CandleIngestionConflict(Base):
    __tablename__ = "candle_ingestion_conflicts"
    __table_args__ = (
        CheckConstraint(
            "conflict_type in ('final_conflict', 'partial_after_final', 'duplicate_final', "
            "'invalid_ohlc', 'timestamp_misalignment')",
            name="candle_ingestion_conflicts_type_allowed",
        ),
        CheckConstraint(
            "resolution in ('skipped', 'kept_existing', 'rejected', 'updated_partial', "
            "'inserted')",
            name="candle_ingestion_conflicts_resolution_allowed",
        ),
        Index("ix_candle_ingestion_conflicts_performance_run_id", "performance_run_id"),
        Index(
            "ix_candle_ingestion_conflicts_symbol_timeframe_timestamp",
            "symbol_id",
            "timeframe",
            "timestamp",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    performance_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("candle_ingestion_performance_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(64), nullable=False)
    existing_candle_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    incoming_candle_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    resolution: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at = created_at_column()
