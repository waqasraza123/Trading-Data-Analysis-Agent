"""add provider polling

Revision ID: 202605021330_provider_polling
Revises: 202605021300
Create Date: 2026-05-02 13:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605021330_provider_polling"
down_revision: str | Sequence[str] | None = "202605021300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_polling_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_symbol", sa.String(length=80), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("limit", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "request_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "response_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("received_candle_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stored_candle_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_candle_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="provider_polling_requests_status_allowed",
        ),
        sa.CheckConstraint(
            "received_candle_count >= 0 and stored_candle_count >= 0 and "
            "skipped_candle_count >= 0",
            name="provider_polling_requests_counts_non_negative",
        ),
        sa.CheckConstraint(
            "limit is null or limit > 0",
            name="provider_polling_requests_limit_positive",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_polling_requests_workspace_provider_symbol_timeframe",
        "provider_polling_requests",
        ["workspace_id", "provider", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_provider_polling_requests_status_created",
        "provider_polling_requests",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_provider_polling_requests_source_id",
        "provider_polling_requests",
        ["source_id"],
    )
    op.create_table(
        "provider_polling_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("polling_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("raw_item_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["polling_request_id"],
            ["provider_polling_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_polling_errors_polling_request_id",
        "provider_polling_errors",
        ["polling_request_id"],
    )
    op.create_index(
        "ix_provider_polling_errors_workspace_id",
        "provider_polling_errors",
        ["workspace_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_polling_errors_workspace_id",
        table_name="provider_polling_errors",
    )
    op.drop_index(
        "ix_provider_polling_errors_polling_request_id",
        table_name="provider_polling_errors",
    )
    op.drop_table("provider_polling_errors")
    op.drop_index(
        "ix_provider_polling_requests_source_id",
        table_name="provider_polling_requests",
    )
    op.drop_index(
        "ix_provider_polling_requests_status_created",
        table_name="provider_polling_requests",
    )
    op.drop_index(
        "ix_provider_polling_requests_workspace_provider_symbol_timeframe",
        table_name="provider_polling_requests",
    )
    op.drop_table("provider_polling_requests")
