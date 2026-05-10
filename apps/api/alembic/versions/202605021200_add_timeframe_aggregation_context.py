"""add timeframe aggregation context

Revision ID: 202605021200_timeframe_aggregation
Revises: f9eb9423c4a2
Create Date: 2026-05-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021200_timeframe_aggregation"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_data_sources_source_type_allowed", "data_sources", type_="check")
    op.create_check_constraint(
        "ck_data_sources_source_type_allowed",
        "data_sources",
        "source_type in ('csv_upload', 'json_import', 'api_polling', "
        "'websocket_live', 'manual_seed', 'chart_screenshot', 'derived_aggregation')",
    )
    op.create_table(
        "candle_aggregation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_timeframe", sa.String(length=16), nullable=False),
        sa.Column("target_timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "expected_base_candle_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "available_base_candle_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "produced_candle_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "skipped_candle_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "incomplete_window_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("aggregation_version", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "available_base_candle_count >= 0",
            name="ck_candle_aggregation_runs_available_base_candle_count_non_negative",
        ),
        sa.CheckConstraint(
            "expected_base_candle_count >= 0",
            name="ck_candle_aggregation_runs_expected_base_candle_count_non_negative",
        ),
        sa.CheckConstraint(
            "incomplete_window_count >= 0",
            name="ck_candle_aggregation_runs_incomplete_window_count_non_negative",
        ),
        sa.CheckConstraint(
            "produced_candle_count >= 0",
            name="ck_candle_aggregation_runs_produced_candle_count_non_negative",
        ),
        sa.CheckConstraint(
            "skipped_candle_count >= 0",
            name="ck_candle_aggregation_runs_skipped_candle_count_non_negative",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name="ck_candle_aggregation_runs_candle_aggregation_run_status_allowed",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candle_aggregation_runs_status_created",
        "candle_aggregation_runs",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_candle_aggregation_runs_workspace_symbol_timeframes",
        "candle_aggregation_runs",
        ["workspace_id", "symbol_id", "base_timeframe", "target_timeframe"],
    )
    op.create_table(
        "derived_candle_lineage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("aggregation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("derived_candle_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_timeframe", sa.String(length=16), nullable=False),
        sa.Column("target_timeframe", sa.String(length=16), nullable=False),
        sa.Column("derived_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_base_count", sa.Integer(), nullable=False),
        sa.Column("actual_base_count", sa.Integer(), nullable=False),
        sa.Column("completeness_score", sa.Numeric(6, 5), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "actual_base_count >= 0",
            name="ck_derived_candle_lineage_derived_actual_base_count_non_negative",
        ),
        sa.CheckConstraint(
            "completeness_score >= 0 and completeness_score <= 1",
            name="ck_derived_candle_lineage_derived_completeness_score_range",
        ),
        sa.CheckConstraint(
            "expected_base_count >= 0",
            name="ck_derived_candle_lineage_derived_expected_base_count_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["aggregation_run_id"], ["candle_aggregation_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["derived_candle_id"], ["candles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_derived_candle_lineage_derived_candle_id",
        "derived_candle_lineage",
        ["derived_candle_id"],
    )
    op.create_index(
        "ix_derived_candle_lineage_workspace_symbol_target_timestamp",
        "derived_candle_lineage",
        ["workspace_id", "symbol_id", "target_timeframe", "derived_timestamp"],
    )
    op.create_table(
        "multi_timeframe_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("primary_timeframe", sa.String(length=16), nullable=False),
        sa.Column(
            "context_timeframes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("context_version", sa.String(length=32), nullable=False),
        sa.Column("trend_alignment", sa.String(length=32), nullable=False),
        sa.Column("volatility_alignment", sa.String(length=32), nullable=False),
        sa.Column("range_alignment", sa.String(length=32), nullable=False),
        sa.Column("agreement_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("agreement_label", sa.String(length=32), nullable=False),
        sa.Column("context_summary", sa.String(length=1000), nullable=False),
        sa.Column("context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "agreement_label in ('strong', 'acceptable', 'mixed', 'conflicting', "
            "'insufficient_context')",
            name="ck_multi_timeframe_contexts_multi_timeframe_agreement_label_allowed",
        ),
        sa.CheckConstraint(
            "agreement_score >= 0 and agreement_score <= 1",
            name="ck_multi_timeframe_contexts_multi_timeframe_agreement_score_range",
        ),
        sa.CheckConstraint(
            "range_alignment in ('aligned', 'partially_aligned', 'conflicting', 'unclear')",
            name="ck_multi_timeframe_contexts_multi_timeframe_range_alignment_allowed",
        ),
        sa.CheckConstraint(
            "trend_alignment in ('aligned', 'partially_aligned', 'conflicting', 'unclear')",
            name="ck_multi_timeframe_contexts_multi_timeframe_trend_alignment_allowed",
        ),
        sa.CheckConstraint(
            "volatility_alignment in ('aligned', 'partially_aligned', 'conflicting', 'unclear')",
            name="ck_multi_timeframe_contexts_multi_timeframe_volatility_alignment_allowed",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_multi_timeframe_contexts_analysis_run_id",
        "multi_timeframe_contexts",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_multi_timeframe_contexts_signal_id", "multi_timeframe_contexts", ["signal_id"]
    )
    op.create_index(
        "ix_multi_timeframe_contexts_workspace_symbol_primary",
        "multi_timeframe_contexts",
        ["workspace_id", "symbol_id", "primary_timeframe"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_multi_timeframe_contexts_workspace_symbol_primary",
        table_name="multi_timeframe_contexts",
    )
    op.drop_index("ix_multi_timeframe_contexts_signal_id", table_name="multi_timeframe_contexts")
    op.drop_index(
        "ix_multi_timeframe_contexts_analysis_run_id", table_name="multi_timeframe_contexts"
    )
    op.drop_table("multi_timeframe_contexts")
    op.drop_index(
        "ix_derived_candle_lineage_workspace_symbol_target_timestamp",
        table_name="derived_candle_lineage",
    )
    op.drop_index(
        "ix_derived_candle_lineage_derived_candle_id", table_name="derived_candle_lineage"
    )
    op.drop_table("derived_candle_lineage")
    op.drop_index(
        "ix_candle_aggregation_runs_workspace_symbol_timeframes",
        table_name="candle_aggregation_runs",
    )
    op.drop_index("ix_candle_aggregation_runs_status_created", table_name="candle_aggregation_runs")
    op.drop_table("candle_aggregation_runs")
    op.drop_constraint("ck_data_sources_source_type_allowed", "data_sources", type_="check")
    op.create_check_constraint(
        "ck_data_sources_source_type_allowed",
        "data_sources",
        "source_type in ('csv_upload', 'json_import', 'api_polling', "
        "'websocket_live', 'manual_seed', 'chart_screenshot')",
    )
