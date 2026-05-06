"""add auth identity api keys

Revision ID: 202605061000_auth_identity_api_keys
Revises: 202605051100_workspace_setup
Create Date: 2026-05-06 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605061000_auth_identity_api_keys"
down_revision: str | Sequence[str] | None = "202605051100_workspace_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_subject", sa.String(length=320), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
            "status in ('active', 'disabled', 'revoked')",
            name="auth_identities_status_allowed",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_auth_identities_provider_subject",
        ),
    )
    op.create_index(
        "ix_auth_identities_user_workspace",
        "auth_identities",
        ["user_id", "workspace_id"],
    )
    op.create_index(
        "ix_auth_identities_workspace_status",
        "auth_identities",
        ["workspace_id", "status"],
    )
    op.create_table(
        "auth_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "scopes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
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
            "status in ('active', 'disabled', 'revoked', 'expired')",
            name="auth_api_keys_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_auth_api_keys_key_hash"),
    )
    op.create_index(
        "ix_auth_api_keys_workspace_status",
        "auth_api_keys",
        ["workspace_id", "status"],
    )
    op.create_index("ix_auth_api_keys_prefix", "auth_api_keys", ["key_prefix"])


def downgrade() -> None:
    op.drop_index("ix_auth_api_keys_prefix", table_name="auth_api_keys")
    op.drop_index("ix_auth_api_keys_workspace_status", table_name="auth_api_keys")
    op.drop_table("auth_api_keys")
    op.drop_index("ix_auth_identities_workspace_status", table_name="auth_identities")
    op.drop_index("ix_auth_identities_user_workspace", table_name="auth_identities")
    op.drop_table("auth_identities")
