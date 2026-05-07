"""add equity data foundation

Revision ID: 202605071100_equity_data
Revises: 202605071000_equity_research
Create Date: 2026-05-07 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605071100_equity_data"
down_revision: str | Sequence[str] | None = "202605071000_equity_research"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def nullable_timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=True)


def zero_count_column(name: str) -> sa.Column:
    return sa.Column(name, sa.Integer(), server_default=sa.text("0"), nullable=False)


def json_object_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "equity_data_provider_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("request_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("credential_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("universe_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticker", sa.String(length=32), nullable=True),
        json_object_column("request_json"),
        json_object_column("response_summary_json"),
        zero_count_column("received_count"),
        zero_count_column("stored_count"),
        zero_count_column("skipped_count"),
        zero_count_column("failed_count"),
        sa.Column("error_message", sa.Text(), nullable=True),
        nullable_timestamp_column("started_at"),
        nullable_timestamp_column("completed_at"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "request_type in ('universe_import', 'symbol_metadata_lookup', "
            "'fundamentals_snapshot', 'earnings_calendar', 'catalyst_import')",
            name="equity_data_provider_requests_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'provider_not_configured', 'provider_not_implemented')",
            name="equity_data_provider_requests_status_allowed",
        ),
        sa.CheckConstraint(
            "received_count >= 0",
            name="equity_data_requests_received_non_negative",
        ),
        sa.CheckConstraint("stored_count >= 0", name="equity_data_requests_stored_non_negative"),
        sa.CheckConstraint("skipped_count >= 0", name="equity_data_requests_skipped_non_negative"),
        sa.CheckConstraint("failed_count >= 0", name="equity_data_requests_failed_non_negative"),
        sa.ForeignKeyConstraint(
            ["credential_ref_id"],
            ["provider_credential_refs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["universe_id"], ["equity_universes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_data_provider_requests_workspace_provider_type_status",
        "equity_data_provider_requests",
        ["workspace_id", "provider", "request_type", "status"],
    )
    op.create_index(
        "ix_equity_data_provider_requests_universe_id",
        "equity_data_provider_requests",
        ["universe_id"],
    )
    op.create_table(
        "equity_symbol_metadata_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("exchange", sa.String(length=80), nullable=True),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("industry", sa.String(length=160), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("market_cap", sa.Numeric(30, 2), nullable=True),
        sa.Column("average_volume", sa.Numeric(30, 10), nullable=True),
        sa.Column("shares_float", sa.Numeric(30, 4), nullable=True),
        sa.Column("is_etf", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        json_object_column("raw_reference_json"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "symbol_id",
            "provider",
            "snapshot_time",
            name="uq_equity_metadata_workspace_symbol_provider_snapshot",
        ),
    )
    op.create_index(
        "ix_equity_symbol_metadata_workspace_symbol_snapshot",
        "equity_symbol_metadata_snapshots",
        ["workspace_id", "symbol_id", "snapshot_time"],
    )
    op.create_index(
        "ix_equity_symbol_metadata_ticker",
        "equity_symbol_metadata_snapshots",
        ["ticker"],
    )
    op.create_index(
        "ix_equity_symbol_metadata_sector_industry",
        "equity_symbol_metadata_snapshots",
        ["sector", "industry"],
    )
    op.create_table(
        "equity_fundamental_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_cap", sa.Numeric(30, 2), nullable=True),
        sa.Column("average_volume", sa.Numeric(30, 10), nullable=True),
        sa.Column("relative_volume", sa.Numeric(18, 6), nullable=True),
        sa.Column("beta", sa.Numeric(18, 6), nullable=True),
        sa.Column("pe_ratio", sa.Numeric(18, 6), nullable=True),
        sa.Column("eps", sa.Numeric(18, 6), nullable=True),
        sa.Column("revenue_growth", sa.Numeric(18, 6), nullable=True),
        sa.Column("earnings_growth", sa.Numeric(18, 6), nullable=True),
        sa.Column("debt_to_equity", sa.Numeric(18, 6), nullable=True),
        sa.Column("free_cash_flow", sa.Numeric(30, 2), nullable=True),
        json_object_column("raw_reference_json"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_fundamental_workspace_symbol_snapshot",
        "equity_fundamental_snapshots",
        ["workspace_id", "symbol_id", "snapshot_time"],
    )
    op.create_table(
        "equity_earnings_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("fiscal_period", sa.String(length=32), nullable=True),
        sa.Column("report_time", sa.String(length=32), nullable=True),
        sa.Column("eps_estimate", sa.Numeric(18, 6), nullable=True),
        sa.Column("eps_actual", sa.Numeric(18, 6), nullable=True),
        sa.Column("revenue_estimate", sa.Numeric(30, 2), nullable=True),
        sa.Column("revenue_actual", sa.Numeric(30, 2), nullable=True),
        sa.Column("importance", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        json_object_column("raw_reference_json"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "importance in ('low', 'medium', 'high', 'unknown')",
            name="equity_earnings_events_importance_allowed",
        ),
        sa.CheckConstraint(
            "status in ('scheduled', 'reported', 'estimated', 'unknown')",
            name="equity_earnings_events_status_allowed",
        ),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_earnings_events_workspace_symbol_event_date",
        "equity_earnings_events",
        ["workspace_id", "symbol_id", "event_date"],
    )
    op.create_index(
        "ix_equity_earnings_events_status_event_date",
        "equity_earnings_events",
        ["status", "event_date"],
    )
    op.create_table(
        "equity_data_import_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_item_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        timestamp_column("created_at"),
        sa.ForeignKeyConstraint(
            ["provider_request_id"],
            ["equity_data_provider_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_data_import_errors_request_id",
        "equity_data_import_errors",
        ["provider_request_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_equity_data_import_errors_request_id", table_name="equity_data_import_errors")
    op.drop_table("equity_data_import_errors")
    op.drop_index(
        "ix_equity_earnings_events_status_event_date", table_name="equity_earnings_events"
    )
    op.drop_index(
        "ix_equity_earnings_events_workspace_symbol_event_date",
        table_name="equity_earnings_events",
    )
    op.drop_table("equity_earnings_events")
    op.drop_index(
        "ix_equity_fundamental_workspace_symbol_snapshot",
        table_name="equity_fundamental_snapshots",
    )
    op.drop_table("equity_fundamental_snapshots")
    op.drop_index(
        "ix_equity_symbol_metadata_sector_industry",
        table_name="equity_symbol_metadata_snapshots",
    )
    op.drop_index(
        "ix_equity_symbol_metadata_ticker",
        table_name="equity_symbol_metadata_snapshots",
    )
    op.drop_index(
        "ix_equity_symbol_metadata_workspace_symbol_snapshot",
        table_name="equity_symbol_metadata_snapshots",
    )
    op.drop_table("equity_symbol_metadata_snapshots")
    op.drop_index(
        "ix_equity_data_provider_requests_universe_id",
        table_name="equity_data_provider_requests",
    )
    op.drop_index(
        "ix_equity_data_provider_requests_workspace_provider_type_status",
        table_name="equity_data_provider_requests",
    )
    op.drop_table("equity_data_provider_requests")
