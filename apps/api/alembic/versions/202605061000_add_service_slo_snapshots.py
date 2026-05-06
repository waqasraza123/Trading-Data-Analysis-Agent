"""add service slo snapshots

Revision ID: 202605061000_service_slo_snapshots
Revises: 202605051100_workspace_setup
Create Date: 2026-05-06 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605061000_service_slo_snapshots"
down_revision: str | Sequence[str] | None = "202605051100_workspace_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_slo_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("slo_version", sa.String(length=32), nullable=False),
        sa.Column(
            "snapshot_json",
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
            "status in ('healthy', 'degraded', 'failing', 'unknown')",
            name="service_slo_snapshots_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_service_slo_snapshots_workspace_created",
        "service_slo_snapshots",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_service_slo_snapshots_status",
        "service_slo_snapshots",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_slo_snapshots_status", table_name="service_slo_snapshots")
    op.drop_index(
        "ix_service_slo_snapshots_workspace_created",
        table_name="service_slo_snapshots",
    )
    op.drop_table("service_slo_snapshots")
