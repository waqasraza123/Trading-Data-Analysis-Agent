"""add market session contexts

Revision ID: 202605020200
Revises: 202605020100
Create Date: 2026-05-02 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605020200"
down_revision: str | Sequence[str] | None = "202605020100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_session_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=False),
        sa.Column("session_version", sa.String(length=32), nullable=False),
        sa.Column("session_label", sa.String(length=40), nullable=False),
        sa.Column("session_region", sa.String(length=16), nullable=False),
        sa.Column("overlap_label", sa.String(length=40), nullable=True),
        sa.Column("is_weekend", sa.Boolean(), nullable=False),
        sa.Column("is_market_open", sa.Boolean(), nullable=False),
        sa.Column("reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "session_label in ('asia', 'london', 'new_york', "
            "'london_new_york_overlap', 'asia_london_overlap', 'off_session', "
            "'weekend', 'crypto_24_7', 'unknown')",
            name="market_session_contexts_session_label_allowed",
        ),
        sa.CheckConstraint(
            "session_region in ('asia', 'europe', 'us', 'global', 'crypto', 'unknown')",
            name="market_session_contexts_session_region_allowed",
        ),
        sa.CheckConstraint(
            "market_type in ('forex', 'crypto', 'stock', 'index', 'commodity')",
            name="market_session_contexts_market_type_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "session_version",
            name="uq_market_session_contexts_analysis_run_version",
        ),
    )
    op.create_index(
        "ix_market_session_contexts_workspace_symbol_timeframe",
        "market_session_contexts",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_market_session_contexts_session_label",
        "market_session_contexts",
        ["session_label"],
    )
    op.create_index(
        "ix_market_session_contexts_market_type",
        "market_session_contexts",
        ["market_type"],
    )
    op.create_index(
        "ix_market_session_contexts_analysis_run_id",
        "market_session_contexts",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_market_session_contexts_signal_id",
        "market_session_contexts",
        ["signal_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_session_contexts_signal_id",
        table_name="market_session_contexts",
    )
    op.drop_index(
        "ix_market_session_contexts_analysis_run_id",
        table_name="market_session_contexts",
    )
    op.drop_index(
        "ix_market_session_contexts_market_type",
        table_name="market_session_contexts",
    )
    op.drop_index(
        "ix_market_session_contexts_session_label",
        table_name="market_session_contexts",
    )
    op.drop_index(
        "ix_market_session_contexts_workspace_symbol_timeframe",
        table_name="market_session_contexts",
    )
    op.drop_table("market_session_contexts")
