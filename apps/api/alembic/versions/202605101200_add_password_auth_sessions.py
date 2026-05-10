"""add password auth sessions

Revision ID: 202605101200_password_auth
Revises: 202605071200_equity_ops
Create Date: 2026-05-10 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605101200_password_auth"
down_revision: str | Sequence[str] | None = "202605071200_equity_ops"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "auth_password_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "status in ('active', 'disabled', 'revoked')",
            name="auth_password_credentials_status_allowed",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_auth_password_credentials_email"),
        sa.UniqueConstraint("user_id", name="uq_auth_password_credentials_user_id"),
    )
    op.create_index(
        "ix_auth_password_credentials_workspace_status",
        "auth_password_credentials",
        ["workspace_id", "status"],
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "status in ('active', 'revoked', 'expired')",
            name="auth_sessions_status_allowed",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
    )
    op.create_index("ix_auth_sessions_user_status", "auth_sessions", ["user_id", "status"])
    op.create_index(
        "ix_auth_sessions_workspace_status",
        "auth_sessions",
        ["workspace_id", "status"],
    )
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_workspace_status", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_status", table_name="auth_sessions")
    op.drop_table("auth_sessions")
    op.drop_index(
        "ix_auth_password_credentials_workspace_status",
        table_name="auth_password_credentials",
    )
    op.drop_table("auth_password_credentials")
