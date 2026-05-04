"""add notification event inbox state

Revision ID: 202605031900_notification_event_inbox
Revises: 202605031800_merge_daily_workflow_heads
Create Date: 2026-05-03 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031900_notification_event_inbox"
down_revision: str | Sequence[str] | None = "202605031800_merge_daily_workflow_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "notification_events_event_type_allowed",
        "notification_events",
        type_="check",
    )
    op.add_column(
        "notification_events",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_events",
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_events",
        sa.Column("acknowledged_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "notification_events",
        sa.Column(
            "inbox_status",
            sa.String(length=24),
            server_default="unread",
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_notification_events_acknowledged_by_user_id_users",
        "notification_events",
        "users",
        ["acknowledged_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "notification_events_event_type_allowed",
        "notification_events",
        "event_type in ('signal.classified', 'signal.review_recommended', "
        "'outcome.evaluated', 'digest.created', 'data_quality.degraded', "
        "'market_memory.stale', 'reasoning.action_due', 'readiness.blocked', "
        "'operator_review.opened', 'scan.completed', 'provider_health.degraded', "
        "'gap_recovery.needed')",
    )
    op.create_check_constraint(
        "notification_events_inbox_status_allowed",
        "notification_events",
        "inbox_status in ('unread', 'read', 'acknowledged', 'archived')",
    )
    op.create_index(
        "ix_notification_events_workspace_inbox_status_created",
        "notification_events",
        ["workspace_id", "inbox_status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_events_workspace_inbox_status_created",
        table_name="notification_events",
    )
    op.drop_constraint(
        "notification_events_inbox_status_allowed",
        "notification_events",
        type_="check",
    )
    op.drop_constraint(
        "notification_events_event_type_allowed",
        "notification_events",
        type_="check",
    )
    op.create_check_constraint(
        "notification_events_event_type_allowed",
        "notification_events",
        "event_type in ('signal.classified', 'signal.review_recommended', "
        "'outcome.evaluated', 'digest.created', 'data_quality.degraded', "
        "'market_memory.stale', 'reasoning.action_due', 'readiness.blocked', "
        "'operator_review.opened')",
    )
    op.drop_constraint(
        "fk_notification_events_acknowledged_by_user_id_users",
        "notification_events",
        type_="foreignkey",
    )
    op.drop_column("notification_events", "inbox_status")
    op.drop_column("notification_events", "acknowledged_by_user_id")
    op.drop_column("notification_events", "acknowledged_at")
    op.drop_column("notification_events", "read_at")
