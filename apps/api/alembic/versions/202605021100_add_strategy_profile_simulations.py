"""add strategy profile simulations

Revision ID: 202605021110_strategy_profile_simulations
Revises: 202604301900
Create Date: 2026-05-02 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021110_strategy_profile_simulations"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_profile_simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_strategy_profile_key", sa.String(length=80), nullable=False),
        sa.Column("base_strategy_profile_version", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("simulation_version", sa.String(length=32), nullable=False),
        sa.Column(
            "proposed_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sampled_signal_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("included_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("excluded_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("changed_decision_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="strategy_profile_simulation_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "sampled_signal_count >= 0 and included_count >= 0 and excluded_count >= 0 "
            "and changed_decision_count >= 0",
            name="strategy_profile_simulation_runs_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_strategy_profile_simulation_runs_workspace_profile",
        "strategy_profile_simulation_runs",
        ["workspace_id", "base_strategy_profile_key"],
    )
    op.create_table(
        "strategy_profile_simulation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("original_classification_status", sa.String(length=32), nullable=False),
        sa.Column("original_bias", sa.String(length=16), nullable=False),
        sa.Column("original_pattern_type", sa.String(length=64), nullable=True),
        sa.Column("original_confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("simulated_classification_status", sa.String(length=32), nullable=False),
        sa.Column("simulated_bias", sa.String(length=16), nullable=False),
        sa.Column("simulated_pattern_type", sa.String(length=64), nullable=True),
        sa.Column("simulated_confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("decision_change_type", sa.String(length=32), nullable=False),
        sa.Column("outcome_label", sa.String(length=40), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "reason_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "decision_change_type in ('unchanged', 'included', 'excluded', 'bias_changed', "
            "'pattern_changed', 'confidence_changed', 'no_candidate')",
            name="strategy_profile_simulation_results_decision_change_type_allowed",
        ),
        sa.CheckConstraint(
            "original_confidence_score is null or "
            "(original_confidence_score >= 0 and original_confidence_score <= 1)",
            name="strategy_profile_simulation_results_original_confidence_range",
        ),
        sa.CheckConstraint(
            "simulated_confidence_score is null or "
            "(simulated_confidence_score >= 0 and simulated_confidence_score <= 1)",
            name="strategy_profile_simulation_results_simulated_confidence_range",
        ),
        sa.CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="strategy_profile_simulation_results_horizon_positive",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["simulation_run_id"],
            ["strategy_profile_simulation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_strategy_profile_simulation_results_run_id",
        "strategy_profile_simulation_results",
        ["simulation_run_id"],
    )
    op.create_index(
        "ix_strategy_profile_simulation_results_signal_id",
        "strategy_profile_simulation_results",
        ["signal_id"],
    )
    op.create_index(
        "ix_strategy_profile_simulation_results_decision_change_type",
        "strategy_profile_simulation_results",
        ["decision_change_type"],
    )
    op.create_index(
        "ix_strategy_profile_simulation_results_outcome_label",
        "strategy_profile_simulation_results",
        ["outcome_label"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_profile_simulation_results_outcome_label",
        table_name="strategy_profile_simulation_results",
    )
    op.drop_index(
        "ix_strategy_profile_simulation_results_decision_change_type",
        table_name="strategy_profile_simulation_results",
    )
    op.drop_index(
        "ix_strategy_profile_simulation_results_signal_id",
        table_name="strategy_profile_simulation_results",
    )
    op.drop_index(
        "ix_strategy_profile_simulation_results_run_id",
        table_name="strategy_profile_simulation_results",
    )
    op.drop_table("strategy_profile_simulation_results")
    op.drop_index(
        "ix_strategy_profile_simulation_runs_workspace_profile",
        table_name="strategy_profile_simulation_runs",
    )
    op.drop_table("strategy_profile_simulation_runs")
