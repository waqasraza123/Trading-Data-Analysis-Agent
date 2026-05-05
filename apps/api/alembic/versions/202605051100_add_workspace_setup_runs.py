"""add workspace setup runs

Revision ID: 202605051100_workspace_setup
Revises: daily routines and provider credential refs
Create Date: 2026-05-05 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605051100_workspace_setup"
down_revision: str | Sequence[str] | None = (
    "202605051100_daily_routines",
    "202605032100_provider_credential_refs",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_setup_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("setup_version", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=64), nullable=False),
        sa.Column(
            "completed_steps_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "skipped_steps_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "failed_steps_json",
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('draft', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="workspace_setup_runs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_setup_runs_workspace_status",
        "workspace_setup_runs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_workspace_setup_runs_user_status",
        "workspace_setup_runs",
        ["user_id", "status"],
    )
    op.create_table(
        "workspace_setup_step_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("setup_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "step_key in ('workspace', 'user', 'symbols', 'data_source', "
            "'credential_reference', 'watchlist', 'scanner_preset', 'preference_profile', "
            "'demo_data', 'readiness_check', 'first_scan')",
            name="workspace_setup_step_results_step_key_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'skipped', 'failed')",
            name="workspace_setup_step_results_status_allowed",
        ),
        sa.ForeignKeyConstraint(["setup_run_id"], ["workspace_setup_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_setup_step_results_run_step",
        "workspace_setup_step_results",
        ["setup_run_id", "step_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_workspace_setup_step_results_run_step",
        table_name="workspace_setup_step_results",
    )
    op.drop_table("workspace_setup_step_results")
    op.drop_index("ix_workspace_setup_runs_user_status", table_name="workspace_setup_runs")
    op.drop_index("ix_workspace_setup_runs_workspace_status", table_name="workspace_setup_runs")
    op.drop_table("workspace_setup_runs")
