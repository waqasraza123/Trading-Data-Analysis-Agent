"""add walk forward validation

Revision ID: 202605031000_walk_forward_validation
Revises: 202605021500_scalable_engines_merge
Create Date: 2026-05-03 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031000_walk_forward_validation"
down_revision: str | Sequence[str] | None = "202605021500_scalable_engines_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "walk_forward_validation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "window_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column("window_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evaluated_signal_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("evaluated_outcome_count", sa.Integer(), server_default="0", nullable=False),
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
            name="walk_forward_validation_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "minimum_sample_size > 0",
            name="walk_forward_validation_runs_minimum_sample_size_positive",
        ),
        sa.CheckConstraint(
            "window_count >= 0 and evaluated_signal_count >= 0 and evaluated_outcome_count >= 0",
            name="walk_forward_validation_runs_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_walk_forward_validation_runs_workspace_created",
        "walk_forward_validation_runs",
        ["workspace_id", "created_at"],
    )
    op.create_table(
        "walk_forward_validation_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("window_index", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
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
        sa.Column("average_confidence_score", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("confidence_alignment_score", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("stability_label", sa.String(length=32), nullable=False),
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
            name="walk_forward_validation_windows_horizon_positive",
        ),
        sa.CheckConstraint(
            "window_index >= 0",
            name="walk_forward_validation_windows_index_non_negative",
        ),
        sa.CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
            "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
            "and reversal_count >= 0 and insufficient_data_count >= 0",
            name="walk_forward_validation_windows_counts_non_negative",
        ),
        sa.CheckConstraint(
            "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
            "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
            "and no_follow_through_rate <= 1",
            name="walk_forward_validation_windows_rates_range",
        ),
        sa.CheckConstraint(
            "average_confidence_score is null or "
            "(average_confidence_score >= 0 and average_confidence_score <= 1)",
            name="walk_forward_validation_windows_average_confidence_range",
        ),
        sa.CheckConstraint(
            "confidence_alignment_score is null or "
            "(confidence_alignment_score >= 0 and confidence_alignment_score <= 1)",
            name="walk_forward_validation_windows_alignment_range",
        ),
        sa.CheckConstraint(
            "stability_label in ('stable', 'improving', 'degrading', 'mixed', "
            "'low_sample', 'insufficient_data')",
            name="walk_forward_validation_windows_stability_label_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["walk_forward_validation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_walk_forward_validation_windows_run_index",
        "walk_forward_validation_windows",
        ["validation_run_id", "window_index"],
    )
    op.create_index(
        "ix_walk_forward_validation_windows_stability_label",
        "walk_forward_validation_windows",
        ["stability_label"],
    )
    op.create_table(
        "walk_forward_validation_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("compared_window_count", sa.Integer(), nullable=False),
        sa.Column("stability_score", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("degradation_detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("improvement_detected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
            name="walk_forward_validation_comparisons_horizon_positive",
        ),
        sa.CheckConstraint(
            "compared_window_count >= 0",
            name="walk_forward_validation_comparisons_window_count_non_negative",
        ),
        sa.CheckConstraint(
            "stability_score >= 0 and stability_score <= 1",
            name="walk_forward_validation_comparisons_stability_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["walk_forward_validation_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_walk_forward_validation_comparisons_run_id",
        "walk_forward_validation_comparisons",
        ["validation_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_walk_forward_validation_comparisons_run_id",
        table_name="walk_forward_validation_comparisons",
    )
    op.drop_table("walk_forward_validation_comparisons")
    op.drop_index(
        "ix_walk_forward_validation_windows_stability_label",
        table_name="walk_forward_validation_windows",
    )
    op.drop_index(
        "ix_walk_forward_validation_windows_run_index",
        table_name="walk_forward_validation_windows",
    )
    op.drop_table("walk_forward_validation_windows")
    op.drop_index(
        "ix_walk_forward_validation_runs_workspace_created",
        table_name="walk_forward_validation_runs",
    )
    op.drop_table("walk_forward_validation_runs")
