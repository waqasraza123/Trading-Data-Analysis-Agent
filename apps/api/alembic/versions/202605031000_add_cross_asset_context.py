"""add cross asset context

Revision ID: 202605031000_cross_asset_context
Revises: 202605021500_scalable_engines_merge
Create Date: 2026-05-03 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031000_cross_asset_context"
down_revision: str | Sequence[str] | None = "202605021500_scalable_engines_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cross_asset_context_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "compared_symbol_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("result_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
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
            "compared_symbol_count >= 0",
            name="cross_asset_context_runs_compared_symbol_count_non_negative",
        ),
        sa.CheckConstraint(
            "result_count >= 0",
            name="cross_asset_context_runs_result_count_non_negative",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="cross_asset_context_runs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["base_symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cross_asset_context_runs_workspace_base_timeframe",
        "cross_asset_context_runs",
        ["workspace_id", "base_symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_cross_asset_context_runs_analysis_run_id",
        "cross_asset_context_runs",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_cross_asset_context_runs_signal_id",
        "cross_asset_context_runs",
        ["signal_id"],
    )
    op.create_table(
        "cross_asset_context_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("compared_symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_move", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("compared_move", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("base_direction", sa.String(length=32), nullable=False),
        sa.Column("compared_direction", sa.String(length=32), nullable=False),
        sa.Column("correlation_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("alignment_label", sa.String(length=32), nullable=False),
        sa.Column("lead_lag_offset_candles", sa.Integer(), nullable=True),
        sa.Column("lead_lag_label", sa.String(length=32), nullable=False),
        sa.Column("divergence_score", sa.Numeric(precision=6, scale=5), nullable=False),
        sa.Column("data_quality_label", sa.String(length=32), nullable=False),
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
        sa.CheckConstraint(
            "alignment_label in ('aligned', 'partially_aligned', 'conflicting', "
            "'divergent', 'insufficient_data')",
            name="cross_asset_context_results_alignment_label_allowed",
        ),
        sa.CheckConstraint(
            "correlation_score >= -1 and correlation_score <= 1",
            name="cross_asset_context_results_correlation_score_range",
        ),
        sa.CheckConstraint(
            "data_quality_label in ('strong', 'acceptable', 'degraded', 'insufficient_data')",
            name="cross_asset_context_results_data_quality_label_allowed",
        ),
        sa.CheckConstraint(
            "divergence_score >= 0 and divergence_score <= 1",
            name="cross_asset_context_results_divergence_score_range",
        ),
        sa.CheckConstraint(
            "lead_lag_label in ('base_leads', 'compared_leads', 'synchronous', "
            "'no_clear_relationship', 'insufficient_data')",
            name="cross_asset_context_results_lead_lag_label_allowed",
        ),
        sa.ForeignKeyConstraint(["base_symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["compared_symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["context_run_id"],
            ["cross_asset_context_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cross_asset_context_results_context_run_id",
        "cross_asset_context_results",
        ["context_run_id"],
    )
    op.create_index(
        "ix_cross_asset_context_results_base_compared_timeframe",
        "cross_asset_context_results",
        ["base_symbol_id", "compared_symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_cross_asset_context_results_alignment_label",
        "cross_asset_context_results",
        ["alignment_label"],
    )
    op.create_index(
        "ix_cross_asset_context_results_lead_lag_label",
        "cross_asset_context_results",
        ["lead_lag_label"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cross_asset_context_results_lead_lag_label",
        table_name="cross_asset_context_results",
    )
    op.drop_index(
        "ix_cross_asset_context_results_alignment_label",
        table_name="cross_asset_context_results",
    )
    op.drop_index(
        "ix_cross_asset_context_results_base_compared_timeframe",
        table_name="cross_asset_context_results",
    )
    op.drop_index(
        "ix_cross_asset_context_results_context_run_id",
        table_name="cross_asset_context_results",
    )
    op.drop_table("cross_asset_context_results")
    op.drop_index("ix_cross_asset_context_runs_signal_id", table_name="cross_asset_context_runs")
    op.drop_index(
        "ix_cross_asset_context_runs_analysis_run_id",
        table_name="cross_asset_context_runs",
    )
    op.drop_index(
        "ix_cross_asset_context_runs_workspace_base_timeframe",
        table_name="cross_asset_context_runs",
    )
    op.drop_table("cross_asset_context_runs")
