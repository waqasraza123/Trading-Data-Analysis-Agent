"""add data retention policies

Revision ID: 202605020940_data_retention_policies
Revises: 202604291530
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020940_data_retention_policies"
down_revision: str | tuple[str, str] | None = "202604291530"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_retention_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "policy_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name=op.f("ck_data_retention_policies_data_retention_policies_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_retention_policies_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_retention_policies")),
    )
    op.create_index(
        "ix_data_retention_policies_workspace_status",
        "data_retention_policies",
        ["workspace_id", "status"],
    )

    op.create_table(
        "data_retention_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planned_action_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("applied_action_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_action_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_action_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
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
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "mode in ('dry_run', 'apply')",
            name=op.f("ck_data_retention_runs_data_retention_runs_mode_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f("ck_data_retention_runs_data_retention_runs_status_allowed"),
        ),
        sa.CheckConstraint(
            "planned_action_count >= 0",
            name=op.f("ck_data_retention_runs_planned_action_count_non_negative"),
        ),
        sa.CheckConstraint(
            "applied_action_count >= 0",
            name=op.f("ck_data_retention_runs_applied_action_count_non_negative"),
        ),
        sa.CheckConstraint(
            "skipped_action_count >= 0",
            name=op.f("ck_data_retention_runs_skipped_action_count_non_negative"),
        ),
        sa.CheckConstraint(
            "failed_action_count >= 0",
            name=op.f("ck_data_retention_runs_failed_action_count_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["policy_id"],
            ["data_retention_policies.id"],
            name=op.f("fk_data_retention_runs_policy_id_data_retention_policies"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_retention_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_retention_runs")),
    )
    op.create_index(
        "ix_data_retention_runs_workspace_created",
        "data_retention_runs",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "data_retention_run_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("retention_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=48), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
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
            "target_type in ('import_batch', 'live_feed_event', 'provider_polling_request', "
            "'llm_explanation_payload', 'reasoning_run_payload', 'dataset_export', "
            "'webhook_outbox_event', 'chart_screenshot_audit_payload')",
            name=op.f("ck_data_retention_run_items_data_retention_run_items_target_type_allowed"),
        ),
        sa.CheckConstraint(
            "action_type in ('archive', 'redact_payload', 'delete_raw_payload', "
            "'delete_record', 'no_action')",
            name=op.f("ck_data_retention_run_items_data_retention_run_items_action_type_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('planned', 'applied', 'skipped', 'failed')",
            name=op.f("ck_data_retention_run_items_data_retention_run_items_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["retention_run_id"],
            ["data_retention_runs.id"],
            name=op.f("fk_data_retention_run_items_retention_run_id_data_retention_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_retention_run_items_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_retention_run_items")),
    )
    op.create_index(
        "ix_data_retention_run_items_retention_run_id",
        "data_retention_run_items",
        ["retention_run_id"],
    )
    op.create_index(
        "ix_data_retention_run_items_target",
        "data_retention_run_items",
        ["target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_data_retention_run_items_target", table_name="data_retention_run_items")
    op.drop_index(
        "ix_data_retention_run_items_retention_run_id",
        table_name="data_retention_run_items",
    )
    op.drop_table("data_retention_run_items")
    op.drop_index("ix_data_retention_runs_workspace_created", table_name="data_retention_runs")
    op.drop_table("data_retention_runs")
    op.drop_index(
        "ix_data_retention_policies_workspace_status",
        table_name="data_retention_policies",
    )
    op.drop_table("data_retention_policies")
