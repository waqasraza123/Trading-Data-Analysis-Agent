"""add intelligence metric snapshots

Revision ID: 202605020100
Revises: 202604301900
Create Date: 2026-05-02 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020100"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_metric_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("snapshot_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metrics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "snapshot_type in ('workspace', 'global', 'module', 'operational_health')",
            name="intelligence_metric_snapshots_snapshot_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="intelligence_metric_snapshots_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_metric_snapshots_workspace_collected",
        "intelligence_metric_snapshots",
        ["workspace_id", "collected_at"],
    )
    op.create_index(
        "ix_intelligence_metric_snapshots_type_collected",
        "intelligence_metric_snapshots",
        ["snapshot_type", "collected_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_intelligence_metric_snapshots_type_collected",
        table_name="intelligence_metric_snapshots",
    )
    op.drop_index(
        "ix_intelligence_metric_snapshots_workspace_collected",
        table_name="intelligence_metric_snapshots",
    )
    op.drop_table("intelligence_metric_snapshots")
