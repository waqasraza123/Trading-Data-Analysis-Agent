"""add candle ingestion performance

Revision ID: 202605061000_candle_ingestion_performance
Revises: 202605051100_workspace_setup
Create Date: 2026-05-06 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605061000_candle_ingestion_performance"
down_revision: str | Sequence[str] | None = "202605051100_workspace_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candle_ingestion_performance_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_polling_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ingestion_mode", sa.String(length=32), nullable=False),
        sa.Column("rows_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_validated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_skipped_duplicate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_conflicted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_failed", sa.Integer(), server_default="0", nullable=False),
        sa.Column("batch_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("elapsed_ms", sa.Integer(), nullable=True),
        sa.Column(
            "diagnostics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
            name="candle_ingestion_performance_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "ingestion_mode in ('csv_import', 'json_import', 'provider_polling', 'bulk_direct')",
            name="candle_ingestion_performance_runs_mode_allowed",
        ),
        sa.CheckConstraint(
            "rows_received >= 0 and rows_validated >= 0 and rows_inserted >= 0 and "
            "rows_updated >= 0 and rows_skipped_duplicate >= 0 and rows_conflicted >= 0 and "
            "rows_failed >= 0 and batch_count >= 0",
            name="candle_ingestion_performance_runs_counts_non_negative",
        ),
        sa.CheckConstraint(
            "elapsed_ms is null or elapsed_ms >= 0",
            name="candle_ingestion_performance_runs_elapsed_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["import_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["provider_polling_request_id"],
            ["provider_polling_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candle_ingestion_performance_runs_workspace_created",
        "candle_ingestion_performance_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_candle_ingestion_performance_runs_import_batch_id",
        "candle_ingestion_performance_runs",
        ["import_batch_id"],
    )
    op.create_table(
        "candle_ingestion_conflicts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("performance_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("conflict_type", sa.String(length=64), nullable=False),
        sa.Column(
            "existing_candle_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "incoming_candle_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("resolution", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "conflict_type in ('final_conflict', 'partial_after_final', 'duplicate_final', "
            "'invalid_ohlc', 'timestamp_misalignment')",
            name="candle_ingestion_conflicts_type_allowed",
        ),
        sa.CheckConstraint(
            "resolution in ('skipped', 'kept_existing', 'rejected', 'updated_partial', "
            "'inserted')",
            name="candle_ingestion_conflicts_resolution_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["performance_run_id"],
            ["candle_ingestion_performance_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candle_ingestion_conflicts_performance_run_id",
        "candle_ingestion_conflicts",
        ["performance_run_id"],
    )
    op.create_index(
        "ix_candle_ingestion_conflicts_symbol_timeframe_timestamp",
        "candle_ingestion_conflicts",
        ["symbol_id", "timeframe", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candle_ingestion_conflicts_symbol_timeframe_timestamp",
        table_name="candle_ingestion_conflicts",
    )
    op.drop_index(
        "ix_candle_ingestion_conflicts_performance_run_id",
        table_name="candle_ingestion_conflicts",
    )
    op.drop_table("candle_ingestion_conflicts")
    op.drop_index(
        "ix_candle_ingestion_performance_runs_import_batch_id",
        table_name="candle_ingestion_performance_runs",
    )
    op.drop_index(
        "ix_candle_ingestion_performance_runs_workspace_created",
        table_name="candle_ingestion_performance_runs",
    )
    op.drop_table("candle_ingestion_performance_runs")
