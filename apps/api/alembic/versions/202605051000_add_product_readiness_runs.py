"""add product readiness runs

Revision ID: 202605051000_product_readiness
Revises: 202605032000_daily_product_workflow_merge
Create Date: 2026-05-05 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605051000_product_readiness"
down_revision: str | Sequence[str] | None = "202605032000_daily_product_workflow_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_readiness_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("readiness_version", sa.String(length=40), nullable=False),
        sa.Column("readiness_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("readiness_label", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "checks_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "blockers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="product_readiness_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "readiness_label in ('ready', 'needs_setup', 'degraded', 'blocked', 'unknown')",
            name="product_readiness_runs_label_allowed",
        ),
        sa.CheckConstraint(
            "readiness_score >= 0 and readiness_score <= 1",
            name="product_readiness_runs_score_range",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_readiness_runs_workspace_created",
        "product_readiness_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_product_readiness_runs_readiness_label",
        "product_readiness_runs",
        ["readiness_label"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_product_readiness_runs_readiness_label",
        table_name="product_readiness_runs",
    )
    op.drop_index(
        "ix_product_readiness_runs_workspace_created",
        table_name="product_readiness_runs",
    )
    op.drop_table("product_readiness_runs")
