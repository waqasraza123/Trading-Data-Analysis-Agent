"""add pattern attribution diagnostics

Revision ID: 202605031200_pattern_attribution
Revises: 202605031100_context_validation_recovery_merge
Create Date: 2026-05-03 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031200_pattern_attribution"
down_revision: str | Sequence[str] | None = "202605031100_context_validation_recovery_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pattern_attribution_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attribution_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column(
            "evaluated_candidate_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "evaluated_signal_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("result_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "evaluated_candidate_count >= 0 and evaluated_signal_count >= 0 "
            "and result_count >= 0",
            name="pattern_attribution_runs_counts_non_negative",
        ),
        sa.CheckConstraint(
            "minimum_sample_size > 0",
            name="pattern_attribution_runs_minimum_sample_size_positive",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="pattern_attribution_runs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pattern_attribution_runs_workspace_created",
        "pattern_attribution_runs",
        ["workspace_id", "created_at"],
    )
    op.create_table(
        "pattern_attribution_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attribution_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=True),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("selected_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("blocked_count", sa.Integer(), nullable=False),
        sa.Column("average_strength_score", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("average_selected_confidence", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("continuation_count", sa.Integer(), nullable=False),
        sa.Column("partial_follow_through_count", sa.Integer(), nullable=False),
        sa.Column("no_follow_through_count", sa.Integer(), nullable=False),
        sa.Column("reversal_count", sa.Integer(), nullable=False),
        sa.Column("insufficient_data_count", sa.Integer(), nullable=False),
        sa.Column("continuation_rate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("reversal_rate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("no_follow_through_rate", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("attribution_label", sa.String(length=40), nullable=False),
        sa.Column("diagnostic_summary", sa.Text(), nullable=False),
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
            "attribution_label in ('strong_selected_behavior', 'often_rejected', "
            "'reversal_prone', 'blocking_effective', 'mixed', 'low_sample', "
            "'insufficient_data')",
            name="pattern_attribution_results_label_allowed",
        ),
        sa.CheckConstraint(
            "average_selected_confidence is null or "
            "(average_selected_confidence >= 0 and average_selected_confidence <= 1)",
            name="pattern_attribution_results_average_selected_confidence_range",
        ),
        sa.CheckConstraint(
            "average_strength_score is null or "
            "(average_strength_score >= 0 and average_strength_score <= 1)",
            name="pattern_attribution_results_average_strength_range",
        ),
        sa.CheckConstraint(
            "candidate_count >= 0 and selected_count >= 0 and rejected_count >= 0 "
            "and blocked_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="pattern_attribution_results_counts_non_negative",
        ),
        sa.CheckConstraint(
            "continuation_rate is null or "
            "(continuation_rate >= 0 and continuation_rate <= 1)",
            name="pattern_attribution_results_continuation_rate_range",
        ),
        sa.CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="pattern_attribution_results_horizon_positive",
        ),
        sa.CheckConstraint(
            "no_follow_through_rate is null or "
            "(no_follow_through_rate >= 0 and no_follow_through_rate <= 1)",
            name="pattern_attribution_results_no_follow_through_rate_range",
        ),
        sa.CheckConstraint(
            "reversal_rate is null or (reversal_rate >= 0 and reversal_rate <= 1)",
            name="pattern_attribution_results_reversal_rate_range",
        ),
        sa.ForeignKeyConstraint(
            ["attribution_run_id"],
            ["pattern_attribution_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pattern_attribution_results_run_id",
        "pattern_attribution_results",
        ["attribution_run_id"],
    )
    op.create_index(
        "ix_pattern_attribution_results_pattern_type",
        "pattern_attribution_results",
        ["pattern_type"],
    )
    op.create_index(
        "ix_pattern_attribution_results_label",
        "pattern_attribution_results",
        ["attribution_label"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pattern_attribution_results_label",
        table_name="pattern_attribution_results",
    )
    op.drop_index(
        "ix_pattern_attribution_results_pattern_type",
        table_name="pattern_attribution_results",
    )
    op.drop_index(
        "ix_pattern_attribution_results_run_id",
        table_name="pattern_attribution_results",
    )
    op.drop_table("pattern_attribution_results")
    op.drop_index(
        "ix_pattern_attribution_runs_workspace_created",
        table_name="pattern_attribution_runs",
    )
    op.drop_table("pattern_attribution_runs")
