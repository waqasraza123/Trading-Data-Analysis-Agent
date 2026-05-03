"""add backfill plans

Revision ID: 202605020910_backfill_plans
Revises: 202604301900
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020910_backfill_plans"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_backfill_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("plan_version", sa.String(length=40), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("target_module", sa.String(length=80), nullable=False),
        sa.Column("target_operation", sa.String(length=80), nullable=False),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("eligible_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("planned_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("blocked_count", sa.Integer(), server_default="0", nullable=False),
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
            "plan_type in ('missing_artifacts', 'stale_artifacts', 'module_backfill', "
            "'outcome_backfill', 'context_backfill', 'quality_backfill', 'dataset_backfill')",
            name="intelligence_backfill_plans_plan_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('draft', 'ready', 'completed', 'cancelled', 'failed')",
            name="intelligence_backfill_plans_status_allowed",
        ),
        sa.CheckConstraint(
            "eligible_count >= 0 and planned_count >= 0 and skipped_count >= 0 "
            "and blocked_count >= 0",
            name="intelligence_backfill_plans_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_backfill_plans_workspace_type_status",
        "intelligence_backfill_plans",
        ["workspace_id", "plan_type", "status"],
    )
    op.create_table(
        "intelligence_backfill_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("backfill_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_operation", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=220), nullable=False),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("skip_reason", sa.String(length=120), nullable=True),
        sa.Column("block_reason", sa.String(length=120), nullable=True),
        sa.Column("execution_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "target_type in ('analysis_run', 'signal', 'outcome', 'reasoning_run', "
            "'chart_screenshot_run', 'news_event', 'workspace')",
            name="intelligence_backfill_items_target_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('planned', 'skipped', 'blocked', 'queued', 'completed', "
            "'failed', 'cancelled')",
            name="intelligence_backfill_items_status_allowed",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high')",
            name="intelligence_backfill_items_priority_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["backfill_plan_id"],
            ["intelligence_backfill_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_intelligence_backfill_items_workspace_idempotency_key",
        ),
    )
    op.create_index(
        "ix_intelligence_backfill_items_plan_status",
        "intelligence_backfill_items",
        ["backfill_plan_id", "status"],
    )
    op.create_index(
        "ix_intelligence_backfill_items_target",
        "intelligence_backfill_items",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_intelligence_backfill_items_target", table_name="intelligence_backfill_items")
    op.drop_index(
        "ix_intelligence_backfill_items_plan_status",
        table_name="intelligence_backfill_items",
    )
    op.drop_table("intelligence_backfill_items")
    op.drop_index(
        "ix_intelligence_backfill_plans_workspace_type_status",
        table_name="intelligence_backfill_plans",
    )
    op.drop_table("intelligence_backfill_plans")
