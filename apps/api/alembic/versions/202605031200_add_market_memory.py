"""add rolling market state memory

Revision ID: 202605031200_market_memory
Revises: 202605031100_context_validation_recovery_merge
Create Date: 2026-05-03 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031200_market_memory"
down_revision: str | Sequence[str] | None = "202605031100_context_validation_recovery_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rolling_market_state_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("state_version", sa.String(length=32), nullable=False),
        sa.Column("latest_final_candle_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data_quality_label", sa.String(length=32), nullable=False),
        sa.Column("freshness_label", sa.String(length=32), nullable=False),
        sa.Column("trend_state", sa.String(length=64), nullable=True),
        sa.Column("volatility_state", sa.String(length=64), nullable=True),
        sa.Column("range_state", sa.String(length=64), nullable=True),
        sa.Column("market_regime_label", sa.String(length=64), nullable=True),
        sa.Column("market_session_label", sa.String(length=64), nullable=True),
        sa.Column("multi_timeframe_label", sa.String(length=64), nullable=True),
        sa.Column("cross_asset_label", sa.String(length=64), nullable=True),
        sa.Column("latest_signal_bias", sa.String(length=32), nullable=True),
        sa.Column("latest_signal_pattern_type", sa.String(length=64), nullable=True),
        sa.Column("latest_signal_confidence_label", sa.String(length=32), nullable=True),
        sa.Column(
            "context_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "data_quality_label in "
            "('strong', 'acceptable', 'degraded', 'poor', 'insufficient', 'unknown')",
            name="rolling_market_state_data_quality_label_allowed",
        ),
        sa.CheckConstraint(
            "freshness_label in ('fresh', 'stale', 'delayed', 'no_data', 'unknown')",
            name="rolling_market_state_freshness_label_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["latest_analysis_run_id"],
            ["analysis_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["latest_outcome_id"], ["signal_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["latest_signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_rolling_market_state_identity",
        "rolling_market_state_snapshots",
        ["workspace_id", "symbol_id", "source_id", "timeframe", "state_version"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "ix_rolling_market_state_workspace_symbol_timeframe",
        "rolling_market_state_snapshots",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_rolling_market_state_workspace_freshness",
        "rolling_market_state_snapshots",
        ["workspace_id", "freshness_label"],
    )
    op.create_index(
        "ix_rolling_market_state_workspace_data_quality",
        "rolling_market_state_snapshots",
        ["workspace_id", "data_quality_label"],
    )
    op.create_index(
        "ix_rolling_market_state_latest_signal_id",
        "rolling_market_state_snapshots",
        ["latest_signal_id"],
    )
    op.create_index(
        "ix_rolling_market_state_latest_analysis_run_id",
        "rolling_market_state_snapshots",
        ["latest_analysis_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rolling_market_state_latest_analysis_run_id",
        table_name="rolling_market_state_snapshots",
    )
    op.drop_index(
        "ix_rolling_market_state_latest_signal_id",
        table_name="rolling_market_state_snapshots",
    )
    op.drop_index(
        "ix_rolling_market_state_workspace_data_quality",
        table_name="rolling_market_state_snapshots",
    )
    op.drop_index(
        "ix_rolling_market_state_workspace_freshness",
        table_name="rolling_market_state_snapshots",
    )
    op.drop_index(
        "ix_rolling_market_state_workspace_symbol_timeframe",
        table_name="rolling_market_state_snapshots",
    )
    op.drop_index("uq_rolling_market_state_identity", table_name="rolling_market_state_snapshots")
    op.drop_table("rolling_market_state_snapshots")
