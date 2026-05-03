"""backtest experiment cohorts

Revision ID: 202605020900_backtest_experiments
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020900_backtest_experiments"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_experiment_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("experiment_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("cohort_dimensions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column("signal_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("outcome_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cohort_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "minimum_sample_size > 0",
            name=op.f(
                "ck_backtest_experiment_runs_backtest_experiment_runs_minimum_sample_size_positive"
            ),
        ),
        sa.CheckConstraint(
            "signal_count >= 0 and outcome_count >= 0 and cohort_count >= 0",
            name=op.f(
                "ck_backtest_experiment_runs_backtest_experiment_runs_counts_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f(
                "ck_backtest_experiment_runs_backtest_experiment_runs_status_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_backtest_experiment_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_experiment_runs")),
    )
    op.create_index(
        "ix_backtest_experiment_runs_status",
        "backtest_experiment_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_backtest_experiment_runs_workspace_created",
        "backtest_experiment_runs",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "backtest_experiment_cohorts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experiment_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_key", sa.String(length=500), nullable=False),
        sa.Column(
            "cohort_dimensions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("evaluated_count", sa.Integer(), nullable=False),
        sa.Column("continuation_count", sa.Integer(), nullable=False),
        sa.Column("partial_follow_through_count", sa.Integer(), nullable=False),
        sa.Column("no_follow_through_count", sa.Integer(), nullable=False),
        sa.Column("reversal_count", sa.Integer(), nullable=False),
        sa.Column("insufficient_data_count", sa.Integer(), nullable=False),
        sa.Column("continuation_rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("reversal_rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("no_follow_through_rate", sa.Numeric(10, 6), nullable=False),
        sa.Column("average_confidence_score", sa.Numeric(10, 6), nullable=True),
        sa.Column(
            "average_max_favorable_move",
            sa.Numeric(24, 10),
            nullable=True,
        ),
        sa.Column("average_max_adverse_move", sa.Numeric(24, 10), nullable=True),
        sa.Column("average_net_move", sa.Numeric(24, 10), nullable=True),
        sa.Column(
            "average_max_favorable_pips",
            sa.Numeric(24, 10),
            nullable=True,
        ),
        sa.Column("average_max_adverse_pips", sa.Numeric(24, 10), nullable=True),
        sa.Column("average_net_pips", sa.Numeric(24, 10), nullable=True),
        sa.Column(
            "average_max_favorable_ticks",
            sa.Numeric(24, 10),
            nullable=True,
        ),
        sa.Column("average_max_adverse_ticks", sa.Numeric(24, 10), nullable=True),
        sa.Column("average_net_ticks", sa.Numeric(24, 10), nullable=True),
        sa.Column("cohort_label", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "cohort_label in ('strong_follow_through', 'mixed_behavior', "
            "'reversal_prone', 'low_sample', 'insufficient_data', 'neutral')",
            name=op.f(
                "ck_backtest_experiment_cohorts_backtest_experiment_cohorts_label_allowed"
            ),
        ),
        sa.CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name=op.f(
                "ck_backtest_experiment_cohorts_backtest_experiment_cohorts_rates_range"
            ),
        ),
        sa.CheckConstraint(
            "horizon_minutes > 0",
            name=op.f(
                "ck_backtest_experiment_cohorts_backtest_experiment_cohorts_horizon_positive"
            ),
        ),
        sa.CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name=op.f(
                "ck_backtest_experiment_cohorts_backtest_experiment_cohorts_counts_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["experiment_run_id"],
            ["backtest_experiment_runs.id"],
            name=op.f(
                "fk_backtest_experiment_cohorts_experiment_run_id_backtest_experiment_runs"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_backtest_experiment_cohorts_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_backtest_experiment_cohorts")),
    )
    op.create_index(
        "ix_backtest_experiment_cohorts_cohort_key",
        "backtest_experiment_cohorts",
        ["cohort_key"],
        unique=False,
    )
    op.create_index(
        "ix_backtest_experiment_cohorts_cohort_label",
        "backtest_experiment_cohorts",
        ["cohort_label"],
        unique=False,
    )
    op.create_index(
        "ix_backtest_experiment_cohorts_experiment_run_id",
        "backtest_experiment_cohorts",
        ["experiment_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_backtest_experiment_cohorts_horizon_minutes",
        "backtest_experiment_cohorts",
        ["horizon_minutes"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_backtest_experiment_cohorts_horizon_minutes",
        table_name="backtest_experiment_cohorts",
    )
    op.drop_index(
        "ix_backtest_experiment_cohorts_experiment_run_id",
        table_name="backtest_experiment_cohorts",
    )
    op.drop_index(
        "ix_backtest_experiment_cohorts_cohort_label",
        table_name="backtest_experiment_cohorts",
    )
    op.drop_index(
        "ix_backtest_experiment_cohorts_cohort_key",
        table_name="backtest_experiment_cohorts",
    )
    op.drop_table("backtest_experiment_cohorts")
    op.drop_index(
        "ix_backtest_experiment_runs_workspace_created",
        table_name="backtest_experiment_runs",
    )
    op.drop_index("ix_backtest_experiment_runs_status", table_name="backtest_experiment_runs")
    op.drop_table("backtest_experiment_runs")
