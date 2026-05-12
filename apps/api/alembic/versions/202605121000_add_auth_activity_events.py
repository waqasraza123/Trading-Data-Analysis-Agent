"""add auth activity events

Revision ID: 202605121000_auth_activity
Revises: 202605101200_password_auth
Create Date: 2026-05-12 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605121000_auth_activity"
down_revision: str | Sequence[str] | None = "202605101200_password_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "auth_activity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("identity_source", sa.String(length=64), nullable=True),
        sa.Column("email_hash", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("client_host_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        timestamp_column("created_at"),
        sa.CheckConstraint(
            "event_type in ('register', 'login', 'logout', 'password_change', 'session_revoke', 'session_revoke_other', 'api_key_create', 'api_key_revoke')",
            name="auth_activity_events_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('success', 'failure')",
            name="auth_activity_events_status_allowed",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_auth_activity_events_user_created",
        "auth_activity_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_auth_activity_events_workspace_created",
        "auth_activity_events",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_auth_activity_events_type_status",
        "auth_activity_events",
        ["event_type", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_activity_events_type_status", table_name="auth_activity_events")
    op.drop_index("ix_auth_activity_events_workspace_created", table_name="auth_activity_events")
    op.drop_index("ix_auth_activity_events_user_created", table_name="auth_activity_events")
    op.drop_table("auth_activity_events")
