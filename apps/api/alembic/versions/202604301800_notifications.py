"""add notification outbox

Revision ID: 202604301800
Revises: 202604301700
Create Date: 2026-04-30 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301800"
down_revision: str | Sequence[str] | None = "202604301700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("min_severity", sa.String(length=16), nullable=False),
        sa.Column(
            "destination_json",
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
            "channel in ('in_app', 'email', 'webhook')",
            name="notification_preferences_channel_allowed",
        ),
        sa.CheckConstraint(
            "event_type in ('signal_ready', 'analysis_completed', 'human_review_requested', "
            "'outcome_ready', 'diagnostic_ready', 'ai_intelligence_ready', 'system_health', "
            "'manual_operator_note')",
            name="notification_preferences_event_type_allowed",
        ),
        sa.CheckConstraint(
            "min_severity in ('info', 'low', 'medium', 'high')",
            name="notification_preferences_min_severity_allowed",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_preferences_workspace_user",
        "notification_preferences",
        ["workspace_id", "user_id"],
    )
    op.create_index(
        "uq_notification_preferences_workspace_user_channel_event",
        "notification_preferences",
        ["workspace_id", "user_id", "channel", "event_type"],
        unique=True,
    )
    op.create_table(
        "notification_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=24), nullable=False),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=220), nullable=False),
        sa.Column(
            "blocked_terms_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
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
            "channel in ('in_app', 'email', 'webhook')",
            name="notification_messages_channel_allowed",
        ),
        sa.CheckConstraint(
            "event_type in ('signal_ready', 'analysis_completed', 'human_review_requested', "
            "'outcome_ready', 'diagnostic_ready', 'ai_intelligence_ready', 'system_health', "
            "'manual_operator_note')",
            name="notification_messages_event_type_allowed",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="notification_messages_severity_allowed",
        ),
        sa.CheckConstraint(
            "status in ('queued', 'sending', 'delivered', 'skipped', 'failed', 'cancelled')",
            name="notification_messages_status_allowed",
        ),
        sa.CheckConstraint(
            "source_type in ('system', 'signal', 'analysis_run', 'reasoning_run', "
            "'action_item', 'outcome', 'diagnostic', 'ai_intelligence', 'screenshot_decision')",
            name="notification_messages_source_type_allowed",
        ),
        sa.CheckConstraint("attempts >= 0", name="notification_messages_attempts_non_negative"),
        sa.CheckConstraint("max_attempts > 0", name="notification_messages_max_attempts_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_notification_messages_workspace_idempotency",
        "notification_messages",
        ["workspace_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_notification_messages_workspace_status_due",
        "notification_messages",
        ["workspace_id", "status", "due_at"],
    )
    op.create_index(
        "ix_notification_messages_user_status_created",
        "notification_messages",
        ["user_id", "status", "created_at"],
    )
    op.create_index(
        "ix_notification_messages_source",
        "notification_messages",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_notification_messages_lock",
        "notification_messages",
        ["locked_by", "locked_until"],
    )
    op.create_table(
        "notification_worker_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", sa.String(length=120), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("batch_limit", sa.Integer(), nullable=False),
        sa.Column("claimed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("delivered_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
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
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('running', 'completed', 'completed_with_warnings', 'failed')",
            name="notification_worker_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "claimed_count >= 0",
            name="notification_worker_runs_claimed_non_negative",
        ),
        sa.CheckConstraint(
            "delivered_count >= 0",
            name="notification_worker_runs_delivered_non_negative",
        ),
        sa.CheckConstraint(
            "skipped_count >= 0",
            name="notification_worker_runs_skipped_non_negative",
        ),
        sa.CheckConstraint(
            "failed_count >= 0",
            name="notification_worker_runs_failed_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_worker_runs_started_at",
        "notification_worker_runs",
        ["started_at"],
    )
    op.create_index(
        "ix_notification_worker_runs_worker_id_started",
        "notification_worker_runs",
        ["worker_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_worker_runs_worker_id_started",
        table_name="notification_worker_runs",
    )
    op.drop_index("ix_notification_worker_runs_started_at", table_name="notification_worker_runs")
    op.drop_table("notification_worker_runs")
    op.drop_index("ix_notification_messages_lock", table_name="notification_messages")
    op.drop_index("ix_notification_messages_source", table_name="notification_messages")
    op.drop_index(
        "ix_notification_messages_user_status_created",
        table_name="notification_messages",
    )
    op.drop_index(
        "ix_notification_messages_workspace_status_due",
        table_name="notification_messages",
    )
    op.drop_index(
        "uq_notification_messages_workspace_idempotency",
        table_name="notification_messages",
    )
    op.drop_table("notification_messages")
    op.drop_index(
        "uq_notification_preferences_workspace_user_channel_event",
        table_name="notification_preferences",
    )
    op.drop_index(
        "ix_notification_preferences_workspace_user",
        table_name="notification_preferences",
    )
    op.drop_table("notification_preferences")
