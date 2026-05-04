"""add webhook outbox

Revision ID: 202605021230_webhook_outbox
Revises: 202604301900
Create Date: 2026-05-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021230_webhook_outbox"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "event_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("signing_secret_ref", sa.String(length=255), nullable=True),
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
            "status in ('active', 'paused', 'archived')",
            name="webhook_subscriptions_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_subscriptions_workspace_status",
        "webhook_subscriptions",
        ["workspace_id", "status"],
    )
    op.create_table(
        "webhook_outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "redaction_warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "delivery_attempt_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
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
            "event_type in ('signal.classified', 'outcome.evaluated', "
            "'reasoning.scenarios_generated', 'action_plan.created', "
            "'action_item.completed', 'action_item.failed', 'quality.finding_created', "
            "'readiness.blocked', 'operator_review.opened')",
            name="webhook_outbox_events_event_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'held', 'cancelled', 'delivered', 'failed')",
            name="webhook_outbox_events_status_allowed",
        ),
        sa.CheckConstraint(
            "delivery_attempt_count >= 0",
            name="webhook_outbox_events_delivery_attempt_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["webhook_subscriptions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_outbox_events_workspace_event_status",
        "webhook_outbox_events",
        ["workspace_id", "event_type", "status"],
    )
    op.create_index(
        "ix_webhook_outbox_events_source",
        "webhook_outbox_events",
        ["source_type", "source_id"],
    )
    op.create_table(
        "webhook_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('skipped', 'failed', 'delivered')",
            name="webhook_delivery_attempts_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["outbox_event_id"],
            ["webhook_outbox_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_webhook_delivery_attempts_outbox_event_id",
        "webhook_delivery_attempts",
        ["outbox_event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_webhook_delivery_attempts_outbox_event_id",
        table_name="webhook_delivery_attempts",
    )
    op.drop_table("webhook_delivery_attempts")
    op.drop_index("ix_webhook_outbox_events_source", table_name="webhook_outbox_events")
    op.drop_index(
        "ix_webhook_outbox_events_workspace_event_status",
        table_name="webhook_outbox_events",
    )
    op.drop_table("webhook_outbox_events")
    op.drop_index(
        "ix_webhook_subscriptions_workspace_status",
        table_name="webhook_subscriptions",
    )
    op.drop_table("webhook_subscriptions")
