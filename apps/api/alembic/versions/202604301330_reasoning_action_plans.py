"""add backend safe reasoning action plans

Revision ID: 202604301330
Revises: 202604301230
Create Date: 2026-04-30 13:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301330"
down_revision: str | tuple[str, str] | None = "202604301230"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reasoning_action_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("plan_version", sa.String(length=40), nullable=False),
        sa.Column("created_from", sa.String(length=32), nullable=False),
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
            "created_from in ('scenario_reasoning', 'deterministic_rules', 'manual_api')",
            name=op.f("ck_reasoning_action_plans_reasoning_action_plans_created_from_allowed"),
        ),
        sa.CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', "
            "'screenshot_decision', 'replay')",
            name=op.f("ck_reasoning_action_plans_reasoning_action_plans_source_type_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'active', 'completed', 'completed_with_warnings', "
            "'cancelled', 'failed')",
            name=op.f("ck_reasoning_action_plans_reasoning_action_plans_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_reasoning_action_plans_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            name=op.f("fk_reasoning_action_plans_reasoning_run_id_llm_reasoning_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_reasoning_action_plans_signal_id_signals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_reasoning_action_plans_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reasoning_action_plans")),
    )
    op.create_index(
        "ix_reasoning_action_plans_workspace_status_created",
        "reasoning_action_plans",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_reasoning_action_plans_reasoning_run_id",
        "reasoning_action_plans",
        ["reasoning_run_id"],
    )
    op.create_table(
        "reasoning_action_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=220), nullable=False),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "action_type in ('evaluate_outcome_after_horizon', 'run_replay', "
            "'run_news_correlation', 'wait_for_more_final_candles', "
            "'request_human_review', 'no_action')",
            name=op.f("ck_reasoning_action_items_reasoning_action_items_action_type_allowed"),
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name=op.f("ck_reasoning_action_items_reasoning_action_items_attempts_non_negative"),
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name=op.f("ck_reasoning_action_items_reasoning_action_items_max_attempts_positive"),
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high')",
            name=op.f("ck_reasoning_action_items_reasoning_action_items_priority_allowed"),
        ),
        sa.CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', "
            "'screenshot_decision', 'replay')",
            name=op.f("ck_reasoning_action_items_reasoning_action_items_source_type_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'due', 'running', 'completed', 'skipped', "
            "'failed', 'cancelled')",
            name=op.f("ck_reasoning_action_items_reasoning_action_items_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["action_plan_id"],
            ["reasoning_action_plans.id"],
            name=op.f("fk_reasoning_action_items_action_plan_id_reasoning_action_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_reasoning_action_items_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            name=op.f("fk_reasoning_action_items_reasoning_run_id_llm_reasoning_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_reasoning_action_items_signal_id_signals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_reasoning_action_items_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reasoning_action_items")),
        sa.UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_reasoning_action_items_workspace_id_idempotency_key",
        ),
    )
    op.create_index(
        "ix_reasoning_action_items_workspace_status_due",
        "reasoning_action_items",
        ["workspace_id", "status", "due_at"],
    )
    op.create_index(
        "ix_reasoning_action_items_signal_action",
        "reasoning_action_items",
        ["signal_id", "action_type"],
    )
    op.create_index(
        "ix_reasoning_action_items_analysis_action",
        "reasoning_action_items",
        ["analysis_run_id", "action_type"],
    )
    op.create_index(
        "ix_reasoning_action_items_reasoning_action",
        "reasoning_action_items",
        ["reasoning_run_id", "action_type"],
    )
    op.create_index(
        "ix_reasoning_action_items_action_status",
        "reasoning_action_items",
        ["action_type", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_reasoning_action_items_action_status", table_name="reasoning_action_items")
    op.drop_index(
        "ix_reasoning_action_items_reasoning_action",
        table_name="reasoning_action_items",
    )
    op.drop_index("ix_reasoning_action_items_analysis_action", table_name="reasoning_action_items")
    op.drop_index("ix_reasoning_action_items_signal_action", table_name="reasoning_action_items")
    op.drop_index(
        "ix_reasoning_action_items_workspace_status_due",
        table_name="reasoning_action_items",
    )
    op.drop_table("reasoning_action_items")
    op.drop_index(
        "ix_reasoning_action_plans_reasoning_run_id",
        table_name="reasoning_action_plans",
    )
    op.drop_index(
        "ix_reasoning_action_plans_workspace_status_created",
        table_name="reasoning_action_plans",
    )
    op.drop_table("reasoning_action_plans")
