from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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


class EquityDataRequestType(StrEnum):
    UNIVERSE_IMPORT = "universe_import"
    SYMBOL_METADATA_LOOKUP = "symbol_metadata_lookup"
    FUNDAMENTALS_SNAPSHOT = "fundamentals_snapshot"
    EARNINGS_CALENDAR = "earnings_calendar"
    CATALYST_IMPORT = "catalyst_import"


class EquityDataRequestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"
    PROVIDER_NOT_IMPLEMENTED = "provider_not_implemented"


class EquityDataOperationType(StrEnum):
    UNIVERSE_IMPORT_ROWS = "universe_import_rows"
    UNIVERSE_IMPORT_FILE = "universe_import_file"
    PROVIDER_UNIVERSE_IMPORT = "provider_universe_import"
    METADATA_ENRICHMENT = "metadata_enrichment"
    FUNDAMENTALS_ENRICHMENT = "fundamentals_enrichment"
    EARNINGS_ENRICHMENT = "earnings_enrichment"
    EARNINGS_TO_CATALYSTS = "earnings_to_catalysts"


class EquityDataOperationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EquityEarningsImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class EquityEarningsStatus(StrEnum):
    SCHEDULED = "scheduled"
    REPORTED = "reported"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class EquityDataProviderRequest(Base):
    __tablename__ = "equity_data_provider_requests"
    __table_args__ = (
        CheckConstraint(
            "request_type in ('universe_import', 'symbol_metadata_lookup', "
            "'fundamentals_snapshot', 'earnings_calendar', 'catalyst_import')",
            name="equity_data_provider_requests_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'provider_not_configured', 'provider_not_implemented')",
            name="equity_data_provider_requests_status_allowed",
        ),
        CheckConstraint("received_count >= 0", name="equity_data_requests_received_non_negative"),
        CheckConstraint("stored_count >= 0", name="equity_data_requests_stored_non_negative"),
        CheckConstraint("skipped_count >= 0", name="equity_data_requests_skipped_non_negative"),
        CheckConstraint("failed_count >= 0", name="equity_data_requests_failed_non_negative"),
        Index(
            "ix_equity_data_provider_requests_workspace_provider_type_status",
            "workspace_id",
            "provider",
            "request_type",
            "status",
        ),
        Index("ix_equity_data_provider_requests_universe_id", "universe_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    request_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    credential_ref_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_credential_refs.id", ondelete="SET NULL"),
        nullable=True,
    )
    universe_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("equity_universes.id", ondelete="SET NULL"),
        nullable=True,
    )
    symbol_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="SET NULL"),
        nullable=True,
    )
    ticker: Mapped[str | None] = mapped_column(String(32), nullable=True)
    request_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    response_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    received_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    stored_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    failed_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquityDataOperation(Base):
    __tablename__ = "equity_data_operations"
    __table_args__ = (
        CheckConstraint(
            "operation_type in ('universe_import_rows', 'universe_import_file', "
            "'provider_universe_import', 'metadata_enrichment', 'fundamentals_enrichment', "
            "'earnings_enrichment', 'earnings_to_catalysts')",
            name="equity_data_operations_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="equity_data_operations_status_allowed",
        ),
        CheckConstraint(
            "progress_current >= 0",
            name="equity_data_operations_progress_current_non_negative",
        ),
        CheckConstraint(
            "progress_total is null or progress_total >= 0",
            name="equity_data_operations_progress_total_non_negative",
        ),
        Index(
            "ix_equity_data_operations_workspace_status_created",
            "workspace_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_equity_data_operations_workspace_type_created",
            "workspace_id",
            "operation_type",
            "created_at",
        ),
        Index("ix_equity_data_operations_provider", "provider_name"),
        Index("ix_equity_data_operations_idempotency", "workspace_id", "idempotency_key"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(240), nullable=True)
    progress_current: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    progress_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    counters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    request_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_summary_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    linked_provider_request_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("equity_data_provider_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_job_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("job_queue_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    dry_run: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()

    @property
    def operation_id(self) -> UUID:
        return self.id


class EquitySymbolMetadataSnapshot(Base):
    __tablename__ = "equity_symbol_metadata_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "symbol_id",
            "provider",
            "snapshot_time",
            name="uq_equity_metadata_workspace_symbol_provider_snapshot",
        ),
        Index(
            "ix_equity_symbol_metadata_workspace_symbol_snapshot",
            "workspace_id",
            "symbol_id",
            "snapshot_time",
        ),
        Index("ix_equity_symbol_metadata_ticker", "ticker"),
        Index("ix_equity_symbol_metadata_sector_industry", "sector", "industry"),
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
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(120), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(160), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    average_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10), nullable=True)
    shares_float: Mapped[Decimal | None] = mapped_column(Numeric(30, 4), nullable=True)
    is_etf: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_reference_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquityFundamentalSnapshot(Base):
    __tablename__ = "equity_fundamental_snapshots"
    __table_args__ = (
        Index(
            "ix_equity_fundamental_workspace_symbol_snapshot",
            "workspace_id",
            "symbol_id",
            "snapshot_time",
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
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    average_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10), nullable=True)
    relative_volume: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    beta: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    pe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    eps: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    revenue_growth: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    earnings_growth: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    free_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    raw_reference_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquityEarningsEvent(Base):
    __tablename__ = "equity_earnings_events"
    __table_args__ = (
        CheckConstraint(
            "importance in ('low', 'medium', 'high', 'unknown')",
            name="equity_earnings_events_importance_allowed",
        ),
        CheckConstraint(
            "status in ('scheduled', 'reported', 'estimated', 'unknown')",
            name="equity_earnings_events_status_allowed",
        ),
        Index(
            "ix_equity_earnings_events_workspace_symbol_event_date",
            "workspace_id",
            "symbol_id",
            "event_date",
        ),
        Index("ix_equity_earnings_events_status_event_date", "status", "event_date"),
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
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_period: Mapped[str | None] = mapped_column(String(32), nullable=True)
    report_time: Mapped[str | None] = mapped_column(String(32), nullable=True)
    eps_estimate: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    eps_actual: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    revenue_estimate: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    revenue_actual: Mapped[Decimal | None] = mapped_column(Numeric(30, 2), nullable=True)
    importance: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_reference_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class EquityDataImportError(Base):
    __tablename__ = "equity_data_import_errors"
    __table_args__ = (Index("ix_equity_data_import_errors_request_id", "provider_request_id"),)

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_request_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("equity_data_provider_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str] = mapped_column(String(80), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_item_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at = created_at_column()
