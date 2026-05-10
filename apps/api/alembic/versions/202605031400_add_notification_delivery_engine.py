"""add notification delivery engine

Revision ID: 202605031400_notification_delivery_engine
Revises: 202605031300_market_memory_drift_attribution_scenario_merge
Create Date: 2026-05-03 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031400_notification_delivery_engine"
down_revision: str | Sequence[str] | None = (
    "202605031300_market_memory_drift_attribution_scenario_merge"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("channel_type", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "event_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "severity_filter_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "quiet_hours_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
            "channel_type in ('webhook', 'email', 'telegram', 'discord')",
            name="notification_channels_channel_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="notification_channels_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_channels_workspace_status_channel_type",
        "notification_channels",
        ["workspace_id", "status", "channel_type"],
    )
    op.create_table(
        "notification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column("dedupe_key", sa.String(length=220), nullable=False),
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
            "event_type in ('signal.classified', 'signal.review_recommended', "
            "'outcome.evaluated', 'digest.created', 'data_quality.degraded', "
            "'market_memory.stale', 'reasoning.action_due', 'readiness.blocked', "
            "'operator_review.opened')",
            name="notification_events_event_type_allowed",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="notification_events_severity_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'held', 'delivered', 'partially_delivered', "
            "'blocked', 'cancelled', 'failed')",
            name="notification_events_status_allowed",
        ),
        sa.CheckConstraint(
            "safety_status in ('passed', 'blocked', 'redacted', 'review_recommended')",
            name="notification_events_safety_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_events_workspace_event_status",
        "notification_events",
        ["workspace_id", "event_type", "status"],
    )
    op.create_index(
        "ix_notification_events_source",
        "notification_events",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_notification_events_dedupe_key",
        "notification_events",
        ["dedupe_key"],
    )
    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=True),
        sa.Column("response_body_excerpt", sa.Text(), nullable=True),
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
            "status in ('pending', 'delivered', 'skipped', 'failed', 'blocked')",
            name="notification_delivery_attempts_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["channel_id"],
            ["notification_channels.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["notification_event_id"],
            ["notification_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_delivery_attempts_notification_event_id",
        "notification_delivery_attempts",
        ["notification_event_id"],
    )
    op.create_index(
        "ix_notification_delivery_attempts_channel_status",
        "notification_delivery_attempts",
        ["channel_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_delivery_attempts_channel_status",
        table_name="notification_delivery_attempts",
    )
    op.drop_index(
        "ix_notification_delivery_attempts_notification_event_id",
        table_name="notification_delivery_attempts",
    )
    op.drop_table("notification_delivery_attempts")
    op.drop_index("ix_notification_events_dedupe_key", table_name="notification_events")
    op.drop_index("ix_notification_events_source", table_name="notification_events")
    op.drop_index(
        "ix_notification_events_workspace_event_status",
        table_name="notification_events",
    )
    op.drop_table("notification_events")
    op.drop_index(
        "ix_notification_channels_workspace_status_channel_type",
        table_name="notification_channels",
    )
    op.drop_table("notification_channels")
