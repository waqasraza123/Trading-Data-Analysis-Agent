"""add cohort drift detection

Revision ID: 202605031200_cohort_drift
Revises: 202605031100_context_validation_recovery_merge
Create Date: 2026-05-03 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031200_cohort_drift"
down_revision: str | Sequence[str] | None = "202605031100_context_validation_recovery_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cohort_drift_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("drift_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "baseline_window_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "comparison_window_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "cohort_dimensions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column("cohort_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "drift_detected_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
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
            name="cohort_drift_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "minimum_sample_size > 0",
            name="cohort_drift_runs_minimum_sample_size_positive",
        ),
        sa.CheckConstraint(
            "cohort_count >= 0 and drift_detected_count >= 0",
            name="cohort_drift_runs_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cohort_drift_runs_workspace_created",
        "cohort_drift_runs",
        ["workspace_id", "created_at"],
    )
    op.create_table(
        "cohort_drift_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("drift_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cohort_key", sa.String(length=500), nullable=False),
        sa.Column(
            "cohort_dimensions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("baseline_sample_size", sa.Integer(), nullable=False),
        sa.Column("comparison_sample_size", sa.Integer(), nullable=False),
        sa.Column("baseline_continuation_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("comparison_continuation_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("continuation_rate_delta", sa.Numeric(10, 6), nullable=True),
        sa.Column("baseline_reversal_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("comparison_reversal_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("reversal_rate_delta", sa.Numeric(10, 6), nullable=True),
        sa.Column("baseline_no_follow_through_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("comparison_no_follow_through_rate", sa.Numeric(10, 6), nullable=True),
        sa.Column("no_follow_through_delta", sa.Numeric(10, 6), nullable=True),
        sa.Column("baseline_confidence_alignment", sa.Numeric(10, 6), nullable=True),
        sa.Column("comparison_confidence_alignment", sa.Numeric(10, 6), nullable=True),
        sa.Column("confidence_alignment_delta", sa.Numeric(10, 6), nullable=True),
        sa.Column("drift_score", sa.Numeric(10, 6), nullable=False),
        sa.Column("drift_label", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
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
            "horizon_minutes > 0",
            name="cohort_drift_results_horizon_positive",
        ),
        sa.CheckConstraint(
            "baseline_sample_size >= 0 and comparison_sample_size >= 0",
            name="cohort_drift_results_sample_sizes_non_negative",
        ),
        sa.CheckConstraint(
            "drift_score >= 0 and drift_score <= 1",
            name="cohort_drift_results_drift_score_range",
        ),
        sa.CheckConstraint(
            "drift_label in ('no_drift', 'mild_drift', 'moderate_drift', 'severe_drift', "
            "'low_sample', 'insufficient_data')",
            name="cohort_drift_results_label_allowed",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="cohort_drift_results_severity_allowed",
        ),
        sa.CheckConstraint(
            "(baseline_continuation_rate is null or "
            "(baseline_continuation_rate >= 0 and baseline_continuation_rate <= 1)) and "
            "(comparison_continuation_rate is null or "
            "(comparison_continuation_rate >= 0 and comparison_continuation_rate <= 1)) and "
            "(baseline_reversal_rate is null or "
            "(baseline_reversal_rate >= 0 and baseline_reversal_rate <= 1)) and "
            "(comparison_reversal_rate is null or "
            "(comparison_reversal_rate >= 0 and comparison_reversal_rate <= 1)) and "
            "(baseline_no_follow_through_rate is null or "
            "(baseline_no_follow_through_rate >= 0 and baseline_no_follow_through_rate <= 1)) and "
            "(comparison_no_follow_through_rate is null or "
            "(comparison_no_follow_through_rate >= 0 and "
            "comparison_no_follow_through_rate <= 1)) and "
            "(baseline_confidence_alignment is null or "
            "(baseline_confidence_alignment >= 0 and baseline_confidence_alignment <= 1)) and "
            "(comparison_confidence_alignment is null or "
            "(comparison_confidence_alignment >= 0 and comparison_confidence_alignment <= 1))",
            name="cohort_drift_results_nullable_rates_range",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drift_run_id"], ["cohort_drift_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cohort_drift_results_drift_run_id",
        "cohort_drift_results",
        ["drift_run_id"],
    )
    op.create_index(
        "ix_cohort_drift_results_drift_label",
        "cohort_drift_results",
        ["drift_label"],
    )
    op.create_index("ix_cohort_drift_results_severity", "cohort_drift_results", ["severity"])
    op.create_index(
        "ix_cohort_drift_results_cohort_key",
        "cohort_drift_results",
        ["cohort_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cohort_drift_results_cohort_key",
        table_name="cohort_drift_results",
    )
    op.drop_index("ix_cohort_drift_results_severity", table_name="cohort_drift_results")
    op.drop_index("ix_cohort_drift_results_drift_label", table_name="cohort_drift_results")
    op.drop_index("ix_cohort_drift_results_drift_run_id", table_name="cohort_drift_results")
    op.drop_table("cohort_drift_results")
    op.drop_index("ix_cohort_drift_runs_workspace_created", table_name="cohort_drift_runs")
    op.drop_table("cohort_drift_runs")
