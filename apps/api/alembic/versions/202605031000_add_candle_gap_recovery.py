"""add candle gap recovery

Revision ID: 202605031000_candle_gap_recovery
Revises: 202605021500_scalable_engines_merge
Create Date: 2026-05-03 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031000_candle_gap_recovery"
down_revision: str | Sequence[str] | None = "202605021500_scalable_engines_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candle_gap_recovery_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recovery_version", sa.String(length=40), nullable=False),
        sa.Column("detection_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detection_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_gap_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("planned_request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_request_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
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
            "status in ('draft', 'ready', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="candle_gap_recovery_plans_status_allowed",
        ),
        sa.CheckConstraint(
            "detected_gap_count >= 0 and planned_request_count >= 0 and "
            "completed_request_count >= 0 and skipped_request_count >= 0 and "
            "failed_request_count >= 0",
            name="candle_gap_recovery_plans_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candle_gap_recovery_plans_workspace_symbol_timeframe",
        "candle_gap_recovery_plans",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_table(
        "candle_gap_recovery_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recovery_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("gap_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("gap_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_candle_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recovery_method", sa.String(length=32), nullable=False),
        sa.Column("provider_polling_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skip_reason", sa.String(length=160), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
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
            "status in ('planned', 'queued', 'completed', 'skipped', 'failed', 'cancelled')",
            name="candle_gap_recovery_items_status_allowed",
        ),
        sa.CheckConstraint(
            "recovery_method in ('provider_polling', 'manual_import', 'unavailable')",
            name="candle_gap_recovery_items_method_allowed",
        ),
        sa.CheckConstraint(
            "expected_candle_count > 0",
            name="candle_gap_recovery_items_expected_count_positive",
        ),
        sa.ForeignKeyConstraint(
            ["provider_polling_request_id"],
            ["provider_polling_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recovery_plan_id"],
            ["candle_gap_recovery_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candle_gap_recovery_items_plan_status",
        "candle_gap_recovery_items",
        ["recovery_plan_id", "status"],
    )
    op.create_index(
        "ix_candle_gap_recovery_items_symbol_timeframe_gap_start",
        "candle_gap_recovery_items",
        ["symbol_id", "timeframe", "gap_start_time"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_candle_gap_recovery_items_symbol_timeframe_gap_start",
        table_name="candle_gap_recovery_items",
    )
    op.drop_index(
        "ix_candle_gap_recovery_items_plan_status",
        table_name="candle_gap_recovery_items",
    )
    op.drop_table("candle_gap_recovery_items")
    op.drop_index(
        "ix_candle_gap_recovery_plans_workspace_symbol_timeframe",
        table_name="candle_gap_recovery_plans",
    )
    op.drop_table("candle_gap_recovery_plans")
