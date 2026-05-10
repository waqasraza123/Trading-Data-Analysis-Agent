"""add confidence calibration analytics

Revision ID: 202605021400
Revises: 202605021330_provider_polling
Create Date: 2026-05-02 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021400"
down_revision: str | Sequence[str] | None = "202605021330_provider_polling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confidence_calibration_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("calibration_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bin_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column("evaluated_signal_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evaluated_outcome_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("bin_count", sa.Integer(), server_default="0", nullable=False),
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
            name="confidence_calibration_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "minimum_sample_size > 0",
            name="confidence_calibration_runs_minimum_sample_size_positive",
        ),
        sa.CheckConstraint(
            "evaluated_signal_count >= 0 and evaluated_outcome_count >= 0 and bin_count >= 0",
            name="confidence_calibration_runs_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_confidence_calibration_runs_workspace_created",
        "confidence_calibration_runs",
        ["workspace_id", "created_at"],
    )
    op.create_table(
        "confidence_calibration_bins",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("calibration_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("bin_label", sa.String(length=32), nullable=False),
        sa.Column("bin_min", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("bin_max", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("evaluated_count", sa.Integer(), nullable=False),
        sa.Column("continuation_count", sa.Integer(), nullable=False),
        sa.Column("partial_follow_through_count", sa.Integer(), nullable=False),
        sa.Column("no_follow_through_count", sa.Integer(), nullable=False),
        sa.Column("reversal_count", sa.Integer(), nullable=False),
        sa.Column("insufficient_data_count", sa.Integer(), nullable=False),
        sa.Column("continuation_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("reversal_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("no_follow_through_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("average_confidence_score", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("confidence_alignment_score", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("calibration_label", sa.String(length=40), nullable=False),
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
            name="confidence_calibration_bins_horizon_positive",
        ),
        sa.CheckConstraint(
            "bin_min >= 0 and bin_min <= 1 and bin_max >= 0 and bin_max <= 1 "
            "and bin_min <= bin_max",
            name="confidence_calibration_bins_bin_range",
        ),
        sa.CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="confidence_calibration_bins_counts_non_negative",
        ),
        sa.CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="confidence_calibration_bins_rates_range",
        ),
        sa.CheckConstraint(
            "average_confidence_score >= 0 and average_confidence_score <= 1",
            name="confidence_calibration_bins_average_confidence_range",
        ),
        sa.CheckConstraint(
            "confidence_alignment_score >= 0 and confidence_alignment_score <= 1",
            name="confidence_calibration_bins_alignment_range",
        ),
        sa.CheckConstraint(
            "calibration_label in ('well_aligned', 'overconfident', 'underconfident', "
            "'mixed', 'low_sample', 'insufficient_data')",
            name="confidence_calibration_bins_label_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["calibration_run_id"],
            ["confidence_calibration_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_confidence_calibration_bins_run_id",
        "confidence_calibration_bins",
        ["calibration_run_id"],
    )
    op.create_index(
        "ix_confidence_calibration_bins_horizon_label",
        "confidence_calibration_bins",
        ["horizon_minutes", "bin_label"],
    )
    op.create_index(
        "ix_confidence_calibration_bins_calibration_label",
        "confidence_calibration_bins",
        ["calibration_label"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_confidence_calibration_bins_calibration_label",
        table_name="confidence_calibration_bins",
    )
    op.drop_index(
        "ix_confidence_calibration_bins_horizon_label",
        table_name="confidence_calibration_bins",
    )
    op.drop_index(
        "ix_confidence_calibration_bins_run_id",
        table_name="confidence_calibration_bins",
    )
    op.drop_table("confidence_calibration_bins")
    op.drop_index(
        "ix_confidence_calibration_runs_workspace_created",
        table_name="confidence_calibration_runs",
    )
    op.drop_table("confidence_calibration_runs")
