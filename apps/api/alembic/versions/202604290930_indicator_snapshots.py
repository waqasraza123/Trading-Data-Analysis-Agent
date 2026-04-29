"""create indicator snapshots

Revision ID: 202604290930
Revises: 202604290900
Create Date: 2026-04-29 09:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604290930"
down_revision: str | None = "202604290900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "indicator_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column(
            "indicators_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_indicator_snapshots_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_indicator_snapshots_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_indicator_snapshots_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_indicator_snapshots")),
    )
    op.create_index(
        "ix_indicator_snapshots_analysis_run_id",
        "indicator_snapshots",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_indicator_snapshots_workspace_symbol_timeframe",
        "indicator_snapshots",
        ["workspace_id", "symbol_id", "timeframe"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_indicator_snapshots_workspace_symbol_timeframe",
        table_name="indicator_snapshots",
    )
    op.drop_index("ix_indicator_snapshots_analysis_run_id", table_name="indicator_snapshots")
    op.drop_table("indicator_snapshots")
