"""add signal outcome evaluation tables

Revision ID: 202604301030
Revises: 202604291430
Create Date: 2026-04-30 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301030"
down_revision: str | tuple[str, str] | None = "202604291430"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_outcomes",
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
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("evaluation_status", sa.String(length=32), nullable=False),
        sa.Column("reference_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_price", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("future_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("future_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("future_candle_count", sa.Integer(), nullable=False),
        sa.Column("max_favorable_move", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("max_adverse_move", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("net_move", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("max_favorable_pips", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("max_adverse_pips", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("net_pips", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("max_favorable_ticks", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("max_adverse_ticks", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("net_ticks", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("direction_followed", sa.Boolean(), nullable=True),
        sa.Column(
            "reversal_detected",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("outcome_label", sa.String(length=40), nullable=False),
        sa.Column("movement_quality", sa.String(length=64), nullable=True),
        sa.Column("evaluation_version", sa.String(length=32), nullable=False),
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
            "bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name=op.f("ck_signal_outcomes_signal_outcomes_bias_allowed"),
        ),
        sa.CheckConstraint(
            "classification_status in ('signal', 'no_signal', 'unclear', 'insufficient_evidence')",
            name=op.f("ck_signal_outcomes_signal_outcomes_classification_status_allowed"),
        ),
        sa.CheckConstraint(
            "evaluation_status in ('pending', 'evaluated', 'insufficient_future_data', "
            "'skipped_not_directional', 'failed')",
            name=op.f("ck_signal_outcomes_signal_outcomes_evaluation_status_allowed"),
        ),
        sa.CheckConstraint(
            "future_candle_count >= 0",
            name=op.f("ck_signal_outcomes_signal_outcomes_future_candle_count_non_negative"),
        ),
        sa.CheckConstraint(
            "horizon_minutes > 0",
            name=op.f("ck_signal_outcomes_signal_outcomes_horizon_positive"),
        ),
        sa.CheckConstraint(
            "outcome_label in ('continuation', 'partial_follow_through', 'no_follow_through', "
            "'reversal', 'sideways_after_signal', 'insufficient_data', 'not_directional', 'failed')",
            name=op.f("ck_signal_outcomes_signal_outcomes_outcome_label_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_signal_outcomes_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_signal_outcomes_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_signal_outcomes_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_signal_outcomes_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_outcomes")),
        sa.UniqueConstraint(
            "signal_id",
            "horizon_minutes",
            "evaluation_version",
            name="uq_signal_outcomes_signal_horizon_version",
        ),
    )
    op.create_index(
        "ix_signal_outcomes_signal_horizon",
        "signal_outcomes",
        ["signal_id", "horizon_minutes"],
    )
    op.create_index(
        "ix_signal_outcomes_workspace_symbol_timeframe_horizon",
        "signal_outcomes",
        ["workspace_id", "symbol_id", "timeframe", "horizon_minutes"],
    )
    op.create_index(
        "ix_signal_outcomes_pattern_horizon",
        "signal_outcomes",
        ["pattern_type", "horizon_minutes"],
    )
    op.create_index(
        "ix_signal_outcomes_strategy_profile_horizon",
        "signal_outcomes",
        ["strategy_profile_key", "horizon_minutes"],
    )
    op.create_index(
        "ix_signal_outcomes_outcome_label",
        "signal_outcomes",
        ["outcome_label"],
    )
    op.create_table(
        "outcome_evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("evaluated_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "evaluated_count >= 0",
            name=op.f("ck_outcome_evaluation_runs_outcome_evaluation_runs_evaluated_count_non_negative"),
        ),
        sa.CheckConstraint(
            "failed_count >= 0",
            name=op.f("ck_outcome_evaluation_runs_outcome_evaluation_runs_failed_count_non_negative"),
        ),
        sa.CheckConstraint(
            "scope_type in ('single_signal', 'analysis_run', 'workspace_backfill', "
            "'symbol_backfill', 'replay_backfill')",
            name=op.f("ck_outcome_evaluation_runs_outcome_evaluation_runs_scope_type_allowed"),
        ),
        sa.CheckConstraint(
            "skipped_count >= 0",
            name=op.f("ck_outcome_evaluation_runs_outcome_evaluation_runs_skipped_count_non_negative"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f("ck_outcome_evaluation_runs_outcome_evaluation_runs_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_outcome_evaluation_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outcome_evaluation_runs")),
    )
    op.create_index(
        "ix_outcome_evaluation_runs_workspace_status",
        "outcome_evaluation_runs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_outcome_evaluation_runs_scope_type",
        "outcome_evaluation_runs",
        ["scope_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_outcome_evaluation_runs_scope_type", table_name="outcome_evaluation_runs")
    op.drop_index(
        "ix_outcome_evaluation_runs_workspace_status",
        table_name="outcome_evaluation_runs",
    )
    op.drop_table("outcome_evaluation_runs")
    op.drop_index("ix_signal_outcomes_outcome_label", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_strategy_profile_horizon", table_name="signal_outcomes")
    op.drop_index("ix_signal_outcomes_pattern_horizon", table_name="signal_outcomes")
    op.drop_index(
        "ix_signal_outcomes_workspace_symbol_timeframe_horizon",
        table_name="signal_outcomes",
    )
    op.drop_index("ix_signal_outcomes_signal_horizon", table_name="signal_outcomes")
    op.drop_table("signal_outcomes")
