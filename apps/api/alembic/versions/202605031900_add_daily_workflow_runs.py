"""add daily workflow runs

Revision ID: 202605031900_daily_workflow_runs
Revises: 202605031800_merge_daily_workflow_heads
Create Date: 2026-05-03 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031900_daily_workflow_runs"
down_revision: str | Sequence[str] | None = "202605031800_merge_daily_workflow_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("workflow_version", sa.String(length=32), nullable=False),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preference_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "steps_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_artifact_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
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
            "workflow_type in ('daily_scan', 'session_scan', 'watchlist_scan', "
            "'data_refresh_only')",
            name="daily_workflow_runs_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="daily_workflow_runs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["watchlist_id"], ["market_watchlists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["preference_profile_id"],
            ["personal_strategy_preference_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_workflow_runs_workspace_created",
        "daily_workflow_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index("ix_daily_workflow_runs_status", "daily_workflow_runs", ["status"])
    op.create_table(
        "daily_workflow_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "output_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("skipped_reason", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "step_key in ('provider_health_refresh', 'gap_recovery_prepare', "
            "'scheduled_scan_run', 'setup_context_generate', 'signal_priority_score', "
            "'market_memory_refresh', 'signal_digest_generate', 'daily_brief_generate')",
            name="daily_workflow_steps_key_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'skipped', 'failed', 'cancelled')",
            name="daily_workflow_steps_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"],
            ["daily_workflow_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_workflow_steps_run_key",
        "daily_workflow_steps",
        ["workflow_run_id", "step_key"],
    )
    op.create_index("ix_daily_workflow_steps_status", "daily_workflow_steps", ["status"])


def downgrade() -> None:
    op.drop_index("ix_daily_workflow_steps_status", table_name="daily_workflow_steps")
    op.drop_index("ix_daily_workflow_steps_run_key", table_name="daily_workflow_steps")
    op.drop_table("daily_workflow_steps")
    op.drop_index("ix_daily_workflow_runs_status", table_name="daily_workflow_runs")
    op.drop_index("ix_daily_workflow_runs_workspace_created", table_name="daily_workflow_runs")
    op.drop_table("daily_workflow_runs")
