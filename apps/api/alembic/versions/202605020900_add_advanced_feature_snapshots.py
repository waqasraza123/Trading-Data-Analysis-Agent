"""add advanced feature snapshots

Revision ID: 202605020900_advanced_feature_snapshots
Revises: 202604301900
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020900_advanced_feature_snapshots"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advanced_feature_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("feature_pack_version", sa.String(length=32), nullable=False),
        sa.Column(
            "impulse_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "correction_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "wick_pressure_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "movement_efficiency_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "compression_expansion_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "swing_structure_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "support_resistance_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "exhaustion_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "liquidity_sweep_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "feature_pack_version",
            name="uq_advanced_feature_snapshots_analysis_run_version",
        ),
    )
    op.create_index(
        "ix_advanced_feature_snapshots_analysis_run_id",
        "advanced_feature_snapshots",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_advanced_feature_snapshots_feature_pack_version",
        "advanced_feature_snapshots",
        ["feature_pack_version"],
        unique=False,
    )
    op.create_index(
        "ix_advanced_feature_snapshots_workspace_symbol_timeframe",
        "advanced_feature_snapshots",
        ["workspace_id", "symbol_id", "timeframe"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_advanced_feature_snapshots_workspace_symbol_timeframe",
        table_name="advanced_feature_snapshots",
    )
    op.drop_index(
        "ix_advanced_feature_snapshots_feature_pack_version",
        table_name="advanced_feature_snapshots",
    )
    op.drop_index(
        "ix_advanced_feature_snapshots_analysis_run_id",
        table_name="advanced_feature_snapshots",
    )
    op.drop_table("advanced_feature_snapshots")
