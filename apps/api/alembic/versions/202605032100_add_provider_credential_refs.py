"""add provider credential refs

Revision ID: 202605032100_provider_credential_refs
Revises: 202605032000_daily_product_workflow_merge
Create Date: 2026-05-03 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605032100_provider_credential_refs"
down_revision: str | Sequence[str] | None = "202605032000_daily_product_workflow_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_credential_refs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("credential_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column(
            "public_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_test_status", sa.String(length=32), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
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
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "credential_type in ('api_key', 'bearer_token', 'basic_auth', 'oauth', "
            "'webhook_secret', 'adc', 'none_required')",
            name="provider_credential_refs_credential_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('active', 'paused', 'revoked', 'missing', 'test_failed')",
            name="provider_credential_refs_status_allowed",
        ),
        sa.CheckConstraint(
            "last_test_status is null or last_test_status in "
            "('passed', 'failed', 'skipped', 'provider_not_configured')",
            name="provider_credential_refs_last_test_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_credential_refs_workspace_provider_status",
        "provider_credential_refs",
        ["workspace_id", "provider", "status"],
    )
    op.create_table(
        "provider_connection_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("test_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "request_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "response_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "test_type in ('configuration_only', 'mock', 'public_endpoint', "
            "'authenticated_endpoint')",
            name="provider_connection_tests_test_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('passed', 'failed', 'skipped', 'provider_not_configured')",
            name="provider_connection_tests_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["credential_ref_id"],
            ["provider_credential_refs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_provider_connection_tests_credential_created",
        "provider_connection_tests",
        ["credential_ref_id", "created_at"],
    )
    op.create_index(
        "ix_provider_connection_tests_workspace_provider_status",
        "provider_connection_tests",
        ["workspace_id", "provider", "status"],
    )
    add_nullable_credential_ref("data_sources")
    add_nullable_credential_ref("live_feed_subscriptions")
    add_nullable_credential_ref("provider_polling_requests")
    add_nullable_credential_ref("notification_channels")
    add_nullable_credential_ref("webhook_subscriptions")


def downgrade() -> None:
    drop_nullable_credential_ref("webhook_subscriptions")
    drop_nullable_credential_ref("notification_channels")
    drop_nullable_credential_ref("provider_polling_requests")
    drop_nullable_credential_ref("live_feed_subscriptions")
    drop_nullable_credential_ref("data_sources")
    op.drop_index(
        "ix_provider_connection_tests_workspace_provider_status",
        table_name="provider_connection_tests",
    )
    op.drop_index(
        "ix_provider_connection_tests_credential_created",
        table_name="provider_connection_tests",
    )
    op.drop_table("provider_connection_tests")
    op.drop_index(
        "ix_provider_credential_refs_workspace_provider_status",
        table_name="provider_credential_refs",
    )
    op.drop_table("provider_credential_refs")


def add_nullable_credential_ref(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column("credential_ref_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        f"fk_{table_name}_credential_ref_id",
        table_name,
        "provider_credential_refs",
        ["credential_ref_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        f"ix_{table_name}_credential_ref_id",
        table_name,
        ["credential_ref_id"],
    )


def drop_nullable_credential_ref(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_credential_ref_id", table_name=table_name)
    op.drop_constraint(f"fk_{table_name}_credential_ref_id", table_name, type_="foreignkey")
    op.drop_column(table_name, "credential_ref_id")
