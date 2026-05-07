"""add equity research mode

Revision ID: 202605071000_equity_research
Revises: 202605061100_production_hardening_merge
Create Date: 2026-05-07 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605071000_equity_research"
down_revision: str | Sequence[str] | None = "202605061100_production_hardening_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def zero_count_column(name: str) -> sa.Column:
    return sa.Column(name, sa.Integer(), server_default=sa.text("0"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "equity_universes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("universe_type", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="equity_universes_status_allowed",
        ),
        sa.CheckConstraint(
            "universe_type in ('manual', 'market_cap', 'sector', 'index', "
            "'watchlist_linked', 'custom')",
            name="equity_universes_type_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_universes_workspace_status",
        "equity_universes",
        ["workspace_id", "status"],
    )
    op.create_table(
        "equity_universe_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("universe_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("sector", sa.String(length=120), nullable=True),
        sa.Column("industry", sa.String(length=160), nullable=True),
        sa.Column("exchange", sa.String(length=80), nullable=True),
        sa.Column("market_cap", sa.Numeric(30, 2), nullable=True),
        sa.Column("average_volume", sa.Numeric(30, 10), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["universe_id"], ["equity_universes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "universe_id",
            "symbol_id",
            name="uq_equity_universe_members_universe_symbol",
        ),
    )
    op.create_index(
        "ix_equity_universe_members_universe_active",
        "equity_universe_members",
        ["universe_id", "is_active"],
    )
    op.create_table(
        "equity_swing_scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("universe_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scan_version", sa.String(length=32), nullable=False),
        sa.Column("scan_profile_key", sa.String(length=80), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        zero_count_column("scanned_symbol_count"),
        zero_count_column("candidate_count"),
        zero_count_column("rejected_count"),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="equity_swing_scan_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "scanned_symbol_count >= 0",
            name="equity_scan_scanned_count_non_negative",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0",
            name="equity_scan_candidate_count_non_negative",
        ),
        sa.CheckConstraint(
            "rejected_count >= 0",
            name="equity_scan_rejected_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["universe_id"], ["equity_universes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["watchlist_id"], ["market_watchlists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_swing_scan_runs_workspace_status_created",
        "equity_swing_scan_runs",
        ["workspace_id", "status", "created_at"],
    )
    op.create_table(
        "equity_swing_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("candidate_status", sa.String(length=32), nullable=False),
        sa.Column("setup_type", sa.String(length=32), nullable=False),
        sa.Column("directional_bias", sa.String(length=16), nullable=False),
        sa.Column("setup_quality_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("setup_quality_label", sa.String(length=32), nullable=False),
        sa.Column("liquidity_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("volume_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("trend_quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("pullback_quality_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("relative_strength_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("momentum_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("volatility_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("catalyst_score", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "confidence_context_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "risk_notes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("setup_context_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "candidate_status in ('candidate', 'needs_confirmation', 'conflicted', 'avoid', "
            "'insufficient_data', 'stale_data')",
            name="equity_swing_candidates_status_allowed",
        ),
        sa.CheckConstraint(
            "setup_type in ('continuation', 'momentum', 'pullback', 'breakout_retest', "
            "'reversal_watch', 'range_break', 'no_clear_setup')",
            name="equity_swing_candidates_setup_type_allowed",
        ),
        sa.CheckConstraint(
            "directional_bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="equity_swing_candidates_bias_allowed",
        ),
        sa.CheckConstraint(
            "setup_quality_label in ('strong_context', 'acceptable_context', 'mixed_context', "
            "'review_required', 'avoid_condition', 'insufficient_context')",
            name="equity_swing_candidates_quality_label_allowed",
        ),
        sa.CheckConstraint(
            "setup_quality_score >= 0 and setup_quality_score <= 1",
            name="equity_swing_candidates_setup_quality_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scan_run_id"], ["equity_swing_scan_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["setup_context_id"], ["setup_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_swing_candidates_scan_run_id",
        "equity_swing_candidates",
        ["scan_run_id"],
    )
    op.create_index(
        "ix_equity_swing_candidates_workspace_symbol_timeframe",
        "equity_swing_candidates",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_equity_swing_candidates_quality_label",
        "equity_swing_candidates",
        ["setup_quality_label"],
    )
    op.create_index(
        "ix_equity_swing_candidates_setup_type",
        "equity_swing_candidates",
        ["setup_type"],
    )
    op.create_index(
        "ix_equity_swing_candidates_status",
        "equity_swing_candidates",
        ["candidate_status"],
    )
    op.create_table(
        "equity_catalyst_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("catalyst_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("importance", sa.String(length=16), nullable=False),
        sa.Column("sentiment", sa.String(length=16), nullable=False),
        sa.Column(
            "raw_reference_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "catalyst_type in ('earnings', 'guidance', 'analyst_rating', 'news', "
            "'sector_event', 'macro_event', 'unusual_volume', 'manual_note')",
            name="equity_catalyst_contexts_type_allowed",
        ),
        sa.CheckConstraint(
            "importance in ('low', 'medium', 'high', 'unknown')",
            name="equity_catalyst_contexts_importance_allowed",
        ),
        sa.CheckConstraint(
            "sentiment in ('bullish', 'bearish', 'neutral', 'mixed', 'unknown')",
            name="equity_catalyst_contexts_sentiment_allowed",
        ),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_catalyst_contexts_workspace_symbol_time",
        "equity_catalyst_contexts",
        ["workspace_id", "symbol_id", "event_time"],
    )
    op.create_index(
        "ix_equity_catalyst_contexts_type_importance",
        "equity_catalyst_contexts",
        ["catalyst_type", "importance"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_equity_catalyst_contexts_type_importance",
        table_name="equity_catalyst_contexts",
    )
    op.drop_index(
        "ix_equity_catalyst_contexts_workspace_symbol_time",
        table_name="equity_catalyst_contexts",
    )
    op.drop_table("equity_catalyst_contexts")
    op.drop_index("ix_equity_swing_candidates_status", table_name="equity_swing_candidates")
    op.drop_index("ix_equity_swing_candidates_setup_type", table_name="equity_swing_candidates")
    op.drop_index("ix_equity_swing_candidates_quality_label", table_name="equity_swing_candidates")
    op.drop_index(
        "ix_equity_swing_candidates_workspace_symbol_timeframe",
        table_name="equity_swing_candidates",
    )
    op.drop_index("ix_equity_swing_candidates_scan_run_id", table_name="equity_swing_candidates")
    op.drop_table("equity_swing_candidates")
    op.drop_index(
        "ix_equity_swing_scan_runs_workspace_status_created",
        table_name="equity_swing_scan_runs",
    )
    op.drop_table("equity_swing_scan_runs")
    op.drop_index(
        "ix_equity_universe_members_universe_active",
        table_name="equity_universe_members",
    )
    op.drop_table("equity_universe_members")
    op.drop_index("ix_equity_universes_workspace_status", table_name="equity_universes")
    op.drop_table("equity_universes")
