"""create feature snapshots

Revision ID: 202604290900
Revises: 202604290620
Create Date: 2026-04-29 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604290900"
down_revision: str | None = "202604290620"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "features_json",
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
            name=op.f("fk_feature_snapshots_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_feature_snapshots_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_feature_snapshots_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feature_snapshots")),
    )
    op.create_index(
        "ix_feature_snapshots_analysis_run_id",
        "feature_snapshots",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_feature_snapshots_workspace_symbol_timeframe",
        "feature_snapshots",
        ["workspace_id", "symbol_id", "timeframe"],
        unique=False,
    )
    op.create_index(
        "ix_feature_snapshots_window",
        "feature_snapshots",
        ["start_time", "end_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_feature_snapshots_window", table_name="feature_snapshots")
    op.drop_index(
        "ix_feature_snapshots_workspace_symbol_timeframe",
        table_name="feature_snapshots",
    )
    op.drop_index("ix_feature_snapshots_analysis_run_id", table_name="feature_snapshots")
    op.drop_table("feature_snapshots")
