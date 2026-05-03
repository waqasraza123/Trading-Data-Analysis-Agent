"""add provider health snapshots

Revision ID: 202605031700_provider_health_snapshots
Revises: 202605031600_dashboard_digest_notifications_journal
Create Date: 2026-05-03 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031700_provider_health_snapshots"
down_revision: str | Sequence[str] | None = "202605031600_dashboard_digest_notifications_journal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("freshness_label", sa.String(length=32), nullable=False),
        sa.Column("latest_final_candle_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_successful_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_failed_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_gap_recovery_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_data_quality_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "consecutive_failure_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("missing_candle_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stale_seconds", sa.Integer(), nullable=True),
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
            "status in ('healthy', 'degraded', 'stale', 'failing', 'unavailable', 'unknown')",
            name="provider_health_snapshots_status_allowed",
        ),
        sa.CheckConstraint(
            "freshness_label in ('fresh', 'delayed', 'stale', 'no_data', 'unknown')",
            name="provider_health_snapshots_freshness_label_allowed",
        ),
        sa.CheckConstraint(
            "consecutive_failure_count >= 0 and missing_candle_count >= 0",
            name="provider_health_snapshots_counts_non_negative",
        ),
        sa.CheckConstraint(
            "stale_seconds is null or stale_seconds >= 0",
            name="provider_health_snapshots_stale_seconds_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["latest_gap_recovery_plan_id"],
            ["candle_gap_recovery_plans.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["latest_data_quality_run_id"],
            ["data_quality_runs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_health_snapshots_workspace_source_status",
        "provider_health_snapshots",
        ["workspace_id", "source_id", "status"],
    )
    op.create_index(
        "ix_provider_health_snapshots_workspace_symbol_timeframe",
        "provider_health_snapshots",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_provider_health_snapshots_provider_status",
        "provider_health_snapshots",
        ["provider", "status"],
    )
    op.create_index(
        "ix_provider_health_snapshots_latest_final_candle_time",
        "provider_health_snapshots",
        ["latest_final_candle_time"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_health_snapshots_latest_final_candle_time",
        table_name="provider_health_snapshots",
    )
    op.drop_index(
        "ix_provider_health_snapshots_provider_status",
        table_name="provider_health_snapshots",
    )
    op.drop_index(
        "ix_provider_health_snapshots_workspace_symbol_timeframe",
        table_name="provider_health_snapshots",
    )
    op.drop_index(
        "ix_provider_health_snapshots_workspace_source_status",
        table_name="provider_health_snapshots",
    )
    op.drop_table("provider_health_snapshots")
