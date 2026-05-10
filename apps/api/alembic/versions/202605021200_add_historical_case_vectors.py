"""add historical case vectors

Revision ID: 202605021200_historical_case_vectors
Revises: f9eb9423c4a2
Create Date: 2026-05-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021200_historical_case_vectors"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historical_case_vectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=True),
        sa.Column("strategy_profile_version", sa.String(length=32), nullable=True),
        sa.Column("pattern_type", sa.String(length=64), nullable=True),
        sa.Column("bias", sa.String(length=16), nullable=False),
        sa.Column("classification_status", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("vector_version", sa.String(length=32), nullable=False),
        sa.Column(
            "vector_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "feature_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "indicator_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("outcome_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "signal_id", "vector_version", name="uq_historical_case_vectors_signal_version"
        ),
    )
    op.create_index(
        "ix_historical_case_vectors_workspace_symbol_timeframe",
        "historical_case_vectors",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_historical_case_vectors_profile_pattern",
        "historical_case_vectors",
        ["strategy_profile_key", "pattern_type"],
    )
    op.create_index(
        "ix_historical_case_vectors_bias_status",
        "historical_case_vectors",
        ["bias", "classification_status"],
    )
    op.create_index(
        "ix_historical_case_vectors_vector_version",
        "historical_case_vectors",
        ["vector_version"],
    )
    op.create_table(
        "historical_case_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("search_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("result_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "results_json",
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
        sa.ForeignKeyConstraint(
            ["source_analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_historical_case_searches_workspace_created",
        "historical_case_searches",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_historical_case_searches_workspace_created", table_name="historical_case_searches"
    )
    op.drop_table("historical_case_searches")
    op.drop_index("ix_historical_case_vectors_vector_version", table_name="historical_case_vectors")
    op.drop_index("ix_historical_case_vectors_bias_status", table_name="historical_case_vectors")
    op.drop_index(
        "ix_historical_case_vectors_profile_pattern", table_name="historical_case_vectors"
    )
    op.drop_index(
        "ix_historical_case_vectors_workspace_symbol_timeframe",
        table_name="historical_case_vectors",
    )
    op.drop_table("historical_case_vectors")
