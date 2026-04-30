"""add reasoning action worker runtime state

Revision ID: 202604301500
Revises: 202604301330
Create Date: 2026-04-30 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301500"
down_revision: str | tuple[str, str] | None = "202604301330"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reasoning_action_items",
        sa.Column("locked_by", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "reasoning_action_items",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_reasoning_action_items_lock",
        "reasoning_action_items",
        ["locked_by", "locked_until"],
    )
    op.create_table(
        "reasoning_action_worker_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", sa.String(length=128), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("batch_limit", sa.Integer(), nullable=False),
        sa.Column("claimed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "batch_limit > 0",
            name=op.f(
                "ck_reasoning_action_worker_runs_reasoning_action_worker_runs_batch_limit_positive"
            ),
        ),
        sa.CheckConstraint(
            "claimed_count >= 0",
            name=op.f(
                "ck_reasoning_action_worker_runs_reasoning_action_worker_runs_claimed_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "completed_count >= 0",
            name=op.f(
                "ck_reasoning_action_worker_runs_reasoning_action_worker_runs_completed_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "failed_count >= 0",
            name=op.f(
                "ck_reasoning_action_worker_runs_reasoning_action_worker_runs_failed_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "skipped_count >= 0",
            name=op.f(
                "ck_reasoning_action_worker_runs_reasoning_action_worker_runs_skipped_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "status in ('running', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f(
                "ck_reasoning_action_worker_runs_reasoning_action_worker_runs_status_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_reasoning_action_worker_runs_workspace_id_workspaces"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reasoning_action_worker_runs")),
    )
    op.create_index(
        "ix_reasoning_action_worker_runs_workspace_status",
        "reasoning_action_worker_runs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_reasoning_action_worker_runs_worker_started",
        "reasoning_action_worker_runs",
        ["worker_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reasoning_action_worker_runs_worker_started",
        table_name="reasoning_action_worker_runs",
    )
    op.drop_index(
        "ix_reasoning_action_worker_runs_workspace_status",
        table_name="reasoning_action_worker_runs",
    )
    op.drop_table("reasoning_action_worker_runs")
    op.drop_index("ix_reasoning_action_items_lock", table_name="reasoning_action_items")
    op.drop_column("reasoning_action_items", "locked_until")
    op.drop_column("reasoning_action_items", "locked_by")
