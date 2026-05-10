"""add operator review queue

Revision ID: 202605020100_operator_review_queue
Revises: 202604301900
Create Date: 2026-05-02 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020100_operator_review_queue"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operator_review_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=48), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("related_analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_action_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_type", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
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
            "source_type in ('chart_screenshot_run', 'signal', 'analysis_run', "
            "'reasoning_run', 'action_item', 'quality_finding', "
            "'calibration_recommendation', 'outcome', 'manual')",
            name="operator_review_items_source_type_allowed",
        ),
        sa.CheckConstraint(
            "review_type in ('extraction_quality', 'signal_quality', "
            "'shadow_disagreement', 'unsafe_llm_output', 'calibration_review', "
            "'action_review', 'outcome_review', 'manual_review')",
            name="operator_review_items_review_type_allowed",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="operator_review_items_priority_allowed",
        ),
        sa.CheckConstraint(
            "status in ('open', 'assigned', 'in_review', 'resolved', 'dismissed', 'cancelled')",
            name="operator_review_items_status_allowed",
        ),
        sa.CheckConstraint(
            "resolution is null or resolution in ('accepted', 'corrected', 'dismissed', "
            "'needs_more_data', 'no_action', 'escalated')",
            name="operator_review_items_resolution_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["related_analysis_run_id"],
            ["analysis_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["related_signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["related_reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_action_item_id"],
            ["reasoning_action_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operator_review_items_workspace_status_priority",
        "operator_review_items",
        ["workspace_id", "status", "priority"],
    )
    op.create_index(
        "ix_operator_review_items_source",
        "operator_review_items",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_operator_review_items_related_signal_id",
        "operator_review_items",
        ["related_signal_id"],
    )
    op.create_index(
        "ix_operator_review_items_related_analysis_run_id",
        "operator_review_items",
        ["related_analysis_run_id"],
    )
    op.create_index(
        "ix_operator_review_items_assigned_status",
        "operator_review_items",
        ["assigned_to_user_id", "status"],
    )
    op.create_index(
        "ix_operator_review_items_review_type_status",
        "operator_review_items",
        ["review_type", "status"],
    )
    op.create_index(
        "uq_operator_review_items_active_source_review",
        "operator_review_items",
        ["workspace_id", "source_type", "source_id", "review_type"],
        unique=True,
        postgresql_where=sa.text("status in ('open', 'assigned', 'in_review')"),
    )

    op.create_table(
        "operator_review_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
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
            "event_type in ('created', 'assigned', 'status_changed', 'resolved', "
            "'dismissed', 'escalated', 'note_added')",
            name="operator_review_events_event_type_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["review_item_id"],
            ["operator_review_items.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operator_review_events_review_item_id",
        "operator_review_events",
        ["review_item_id"],
    )
    op.create_index(
        "ix_operator_review_events_workspace_created",
        "operator_review_events",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operator_review_events_workspace_created",
        table_name="operator_review_events",
    )
    op.drop_index("ix_operator_review_events_review_item_id", table_name="operator_review_events")
    op.drop_table("operator_review_events")
    op.drop_index(
        "uq_operator_review_items_active_source_review",
        table_name="operator_review_items",
    )
    op.drop_index("ix_operator_review_items_review_type_status", table_name="operator_review_items")
    op.drop_index("ix_operator_review_items_assigned_status", table_name="operator_review_items")
    op.drop_index(
        "ix_operator_review_items_related_analysis_run_id",
        table_name="operator_review_items",
    )
    op.drop_index(
        "ix_operator_review_items_related_signal_id",
        table_name="operator_review_items",
    )
    op.drop_index("ix_operator_review_items_source", table_name="operator_review_items")
    op.drop_index(
        "ix_operator_review_items_workspace_status_priority",
        table_name="operator_review_items",
    )
    op.drop_table("operator_review_items")
