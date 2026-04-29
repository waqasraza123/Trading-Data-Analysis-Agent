from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ImportBatchStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'processing', 'completed', "
            "'completed_with_warnings', 'failed', 'cancelled')",
            name="status_allowed",
        ),
        CheckConstraint("rows_received >= 0", name="rows_received_non_negative"),
        CheckConstraint("rows_valid >= 0", name="rows_valid_non_negative"),
        CheckConstraint("rows_invalid >= 0", name="rows_invalid_non_negative"),
        CheckConstraint("duplicates_skipped >= 0", name="duplicates_skipped_non_negative"),
        CheckConstraint(
            "missing_candles_detected >= 0",
            name="missing_candles_detected_non_negative",
        ),
        CheckConstraint(
            "data_quality_score is null or (data_quality_score >= 0 and data_quality_score <= 1)",
            name="data_quality_score_range",
        ),
        Index("ix_import_batches_workspace_id", "workspace_id"),
        Index("ix_import_batches_symbol_timeframe", "symbol_id", "timeframe"),
        Index("ix_import_batches_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    rows_received: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_valid: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_invalid: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    duplicates_skipped: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    missing_candles_detected: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    data_quality_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 5), nullable=True)
    error_summary_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class ImportError(Base):
    __tablename__ = "import_errors"
    __table_args__ = (
        Index("ix_import_errors_import_batch_id", "import_batch_id"),
        Index("ix_import_errors_error_code", "error_code"),
    )

    id = uuid_primary_key()
    import_batch_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("import_batches.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(nullable=False)
    error_code: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_row_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at = created_at_column()
