from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ProviderPollingRequestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ProviderPollingRequest(Base):
    __tablename__ = "provider_polling_requests"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="provider_polling_requests_status_allowed",
        ),
        CheckConstraint(
            "received_candle_count >= 0 and stored_candle_count >= 0 and "
            "skipped_candle_count >= 0",
            name="provider_polling_requests_counts_non_negative",
        ),
        CheckConstraint(
            "limit is null or limit > 0",
            name="provider_polling_requests_limit_positive",
        ),
        Index(
            "ix_provider_polling_requests_workspace_provider_symbol_timeframe",
            "workspace_id",
            "provider",
            "symbol_id",
            "timeframe",
        ),
        Index(
            "ix_provider_polling_requests_status_created",
            "status",
            "created_at",
        ),
        Index("ix_provider_polling_requests_source_id", "source_id"),
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
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(80), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    credential_ref_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_credential_refs.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    limit: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    request_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    response_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    received_candle_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        server_default="0",
    )
    stored_candle_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    skipped_candle_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class ProviderPollingError(Base):
    __tablename__ = "provider_polling_errors"
    __table_args__ = (
        Index(
            "ix_provider_polling_errors_polling_request_id",
            "polling_request_id",
        ),
        Index(
            "ix_provider_polling_errors_workspace_id",
            "workspace_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    polling_request_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_polling_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_item_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at = created_at_column()
