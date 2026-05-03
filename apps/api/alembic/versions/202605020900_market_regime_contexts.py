"""market regime contexts

Revision ID: 202605020900
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020900"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_regime_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("regime_version", sa.String(length=32), nullable=False),
        sa.Column("trend_regime", sa.String(length=32), nullable=False),
        sa.Column("volatility_regime", sa.String(length=32), nullable=False),
        sa.Column("range_regime", sa.String(length=32), nullable=False),
        sa.Column("liquidity_regime", sa.String(length=32), nullable=True),
        sa.Column("data_quality_label", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence_label", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column(
            "feature_inputs_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "indicator_inputs_json",
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
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "trend_regime in ('uptrend', 'downtrend', 'sideways', 'mixed', 'unclear')",
            name="ck_market_regime_contexts_market_regime_trend_allowed",
        ),
        sa.CheckConstraint(
            "volatility_regime in "
            "('compressed', 'normal', 'expanding', 'high_volatility', 'spike', 'unclear')",
            name="ck_market_regime_contexts_market_regime_volatility_allowed",
        ),
        sa.CheckConstraint(
            "range_regime in "
            "('inside_range', 'breakout', 'breakdown', 'fakeout_risk', 'range_retest', 'unclear')",
            name="ck_market_regime_contexts_market_regime_range_allowed",
        ),
        sa.CheckConstraint(
            "data_quality_label in ('strong', 'acceptable', 'degraded', 'insufficient')",
            name="ck_market_regime_contexts_market_regime_data_quality_allowed",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 and confidence_score <= 1",
            name="ck_market_regime_contexts_market_regime_confidence_score_range",
        ),
        sa.CheckConstraint(
            "confidence_label in ('low', 'medium', 'high', 'very_high')",
            name="ck_market_regime_contexts_market_regime_confidence_label_allowed",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_run_id",
            "regime_version",
            name="uq_market_regime_contexts_analysis_run_version",
        ),
    )
    op.create_index(
        "ix_market_regime_contexts_workspace_symbol_timeframe",
        "market_regime_contexts",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_market_regime_contexts_analysis_run_id",
        "market_regime_contexts",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_market_regime_contexts_signal_id",
        "market_regime_contexts",
        ["signal_id"],
    )
    op.create_index(
        "ix_market_regime_contexts_trend_regime",
        "market_regime_contexts",
        ["trend_regime"],
    )
    op.create_index(
        "ix_market_regime_contexts_volatility_regime",
        "market_regime_contexts",
        ["volatility_regime"],
    )
    op.create_index(
        "ix_market_regime_contexts_range_regime",
        "market_regime_contexts",
        ["range_regime"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_regime_contexts_range_regime", table_name="market_regime_contexts")
    op.drop_index("ix_market_regime_contexts_volatility_regime", table_name="market_regime_contexts")
    op.drop_index("ix_market_regime_contexts_trend_regime", table_name="market_regime_contexts")
    op.drop_index("ix_market_regime_contexts_signal_id", table_name="market_regime_contexts")
    op.drop_index("ix_market_regime_contexts_analysis_run_id", table_name="market_regime_contexts")
    op.drop_index(
        "ix_market_regime_contexts_workspace_symbol_timeframe",
        table_name="market_regime_contexts",
    )
    op.drop_table("market_regime_contexts")
