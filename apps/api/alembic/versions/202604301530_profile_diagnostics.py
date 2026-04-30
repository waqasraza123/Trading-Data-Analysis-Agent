"""add outcome based profile diagnostics

Revision ID: 202604301530
Revises: 202604301330
Create Date: 2026-04-30 15:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301530"
down_revision: str | tuple[str, str] | None = "202604301330"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIAGNOSTIC_LABEL_ALLOWED = (
    "diagnostic_label in ('strong_follow_through', 'mixed_behavior', 'reversal_prone', "
    "'low_sample', 'insufficient_data', 'needs_threshold_review', 'neutral')"
)
DIAGNOSTIC_RATES_RANGE = (
    "continuation_rate >= 0 and continuation_rate <= 1 and reversal_rate >= 0 "
    "and reversal_rate <= 1 and no_follow_through_rate >= 0 "
    "and no_follow_through_rate <= 1"
)
CONFIDENCE_ALIGNMENT_RANGE = (
    "confidence_alignment_score is null or "
    "(confidence_alignment_score >= 0 and confidence_alignment_score <= 1)"
)
PROFILE_DIAGNOSTIC_COUNTS_NON_NEGATIVE = (
    "sample_size >= 0 and evaluated_count >= 0 and continuation_count >= 0 "
    "and partial_follow_through_count >= 0 and no_follow_through_count >= 0 "
    "and reversal_count >= 0 and insufficient_data_count >= 0"
)
RECOMMENDATION_TYPE_ALLOWED = (
    "recommendation_type in ('review_minimum_confidence', 'review_candidate_strength', "
    "'tighten_profile_filter', 'loosen_profile_filter', 'review_pattern_detector', "
    "'increase_sample_size', 'monitor_symbol_timeframe', 'no_change')"
)


def upgrade() -> None:
    op.create_table(
        "strategy_profile_diagnostic_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("horizons_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("minimum_sample_size", sa.Integer(), nullable=False),
        sa.Column(
            "evaluated_signal_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "evaluated_outcome_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "diagnostics_created_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "recommendations_created_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "diagnostics_created_count >= 0",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_diagnostics_created_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "evaluated_outcome_count >= 0",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_evaluated_outcome_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "evaluated_signal_count >= 0",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_evaluated_signal_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "minimum_sample_size > 0",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_minimum_sample_size_positive"
            ),
        ),
        sa.CheckConstraint(
            "recommendations_created_count >= 0",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_recommendations_created_count_non_negative"
            ),
        ),
        sa.CheckConstraint(
            "scope_type in ('workspace', 'strategy_profile', 'symbol', 'timeframe', "
            "'pattern', 'custom')",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_scope_type_allowed"
            ),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f(
                "ck_strategy_profile_diagnostic_runs_strategy_profile_diagnostic_runs_status_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_strategy_profile_diagnostic_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_profile_diagnostic_runs")),
    )
    op.create_index(
        "ix_strategy_profile_diagnostic_runs_workspace_status",
        "strategy_profile_diagnostic_runs",
        ["workspace_id", "status"],
    )
    op.create_table(
        "strategy_profile_diagnostics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnostic_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=False),
        sa.Column("strategy_profile_version", sa.String(length=32), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
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
        sa.Column("average_max_favorable_move", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_max_adverse_move", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_net_move", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_max_favorable_pips", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_max_adverse_pips", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_net_pips", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_max_favorable_ticks", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_max_adverse_ticks", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("average_net_ticks", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("confidence_alignment_score", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("diagnostic_label", sa.String(length=40), nullable=False),
        sa.Column("diagnostic_summary", sa.Text(), nullable=False),
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
            CONFIDENCE_ALIGNMENT_RANGE,
            name=op.f(
                "ck_strategy_profile_diagnostics_strategy_profile_diagnostics_confidence_alignment_range"
            ),
        ),
        sa.CheckConstraint(
            DIAGNOSTIC_RATES_RANGE,
            name=op.f("ck_strategy_profile_diagnostics_strategy_profile_diagnostics_rates_range"),
        ),
        sa.CheckConstraint(
            DIAGNOSTIC_LABEL_ALLOWED,
            name=op.f("ck_strategy_profile_diagnostics_strategy_profile_diagnostics_label_allowed"),
        ),
        sa.CheckConstraint(
            "horizon_minutes > 0",
            name=op.f(
                "ck_strategy_profile_diagnostics_strategy_profile_diagnostics_horizon_positive"
            ),
        ),
        sa.CheckConstraint(
            PROFILE_DIAGNOSTIC_COUNTS_NON_NEGATIVE,
            name=op.f(
                "ck_strategy_profile_diagnostics_strategy_profile_diagnostics_counts_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_run_id"],
            ["strategy_profile_diagnostic_runs.id"],
            name=op.f(
                "fk_strategy_profile_diagnostics_diagnostic_run_id_strategy_profile_diagnostic_runs"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_strategy_profile_diagnostics_symbol_id_symbols"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_strategy_profile_diagnostics_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_profile_diagnostics")),
    )
    op.create_index(
        "ix_strategy_profile_diagnostics_workspace_profile_horizon",
        "strategy_profile_diagnostics",
        ["workspace_id", "strategy_profile_key", "horizon_minutes"],
    )
    op.create_index(
        "ix_strategy_profile_diagnostics_diagnostic_run_id",
        "strategy_profile_diagnostics",
        ["diagnostic_run_id"],
    )
    op.create_index(
        "ix_strategy_profile_diagnostics_diagnostic_label",
        "strategy_profile_diagnostics",
        ["diagnostic_label"],
    )
    op.create_table(
        "pattern_outcome_diagnostics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnostic_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("evaluated_count", sa.Integer(), nullable=False),
        sa.Column("continuation_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("reversal_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("no_follow_through_rate", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("average_confidence_score", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("confidence_alignment_score", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("diagnostic_label", sa.String(length=40), nullable=False),
        sa.Column("diagnostic_summary", sa.Text(), nullable=False),
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
            CONFIDENCE_ALIGNMENT_RANGE,
            name=op.f(
                "ck_pattern_outcome_diagnostics_pattern_outcome_diagnostics_confidence_alignment_range"
            ),
        ),
        sa.CheckConstraint(
            DIAGNOSTIC_RATES_RANGE,
            name=op.f("ck_pattern_outcome_diagnostics_pattern_outcome_diagnostics_rates_range"),
        ),
        sa.CheckConstraint(
            DIAGNOSTIC_LABEL_ALLOWED,
            name=op.f("ck_pattern_outcome_diagnostics_pattern_outcome_diagnostics_label_allowed"),
        ),
        sa.CheckConstraint(
            "horizon_minutes > 0",
            name=op.f(
                "ck_pattern_outcome_diagnostics_pattern_outcome_diagnostics_horizon_positive"
            ),
        ),
        sa.CheckConstraint(
            "sample_size >= 0 and evaluated_count >= 0",
            name=op.f(
                "ck_pattern_outcome_diagnostics_pattern_outcome_diagnostics_counts_non_negative"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_run_id"],
            ["strategy_profile_diagnostic_runs.id"],
            name=op.f(
                "fk_pattern_outcome_diagnostics_diagnostic_run_id_strategy_profile_diagnostic_runs"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_pattern_outcome_diagnostics_symbol_id_symbols"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_pattern_outcome_diagnostics_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_outcome_diagnostics")),
    )
    op.create_index(
        "ix_pattern_outcome_diagnostics_workspace_pattern_horizon",
        "pattern_outcome_diagnostics",
        ["workspace_id", "pattern_type", "horizon_minutes"],
    )
    op.create_index(
        "ix_pattern_outcome_diagnostics_diagnostic_run_id",
        "pattern_outcome_diagnostics",
        ["diagnostic_run_id"],
    )
    op.create_table(
        "calibration_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnostic_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recommendation_type", sa.String(length=48), nullable=False),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=True),
        sa.Column("strategy_profile_version", sa.String(length=32), nullable=True),
        sa.Column("pattern_type", sa.String(length=64), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "suggested_change_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name=op.f(
                "ck_calibration_recommendations_calibration_recommendations_horizon_positive"
            ),
        ),
        sa.CheckConstraint(
            RECOMMENDATION_TYPE_ALLOWED,
            name=op.f("ck_calibration_recommendations_calibration_recommendations_type_allowed"),
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name=op.f(
                "ck_calibration_recommendations_calibration_recommendations_severity_allowed"
            ),
        ),
        sa.CheckConstraint(
            "status in ('open', 'acknowledged', 'dismissed', 'applied_manually')",
            name=op.f("ck_calibration_recommendations_calibration_recommendations_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["diagnostic_run_id"],
            ["strategy_profile_diagnostic_runs.id"],
            name=op.f(
                "fk_calibration_recommendations_diagnostic_run_id_strategy_profile_diagnostic_runs"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_calibration_recommendations_symbol_id_symbols"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_calibration_recommendations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calibration_recommendations")),
    )
    op.create_index(
        "ix_calibration_recommendations_workspace_status_severity",
        "calibration_recommendations",
        ["workspace_id", "status", "severity"],
    )
    op.create_index(
        "ix_calibration_recommendations_strategy_profile_status",
        "calibration_recommendations",
        ["strategy_profile_key", "status"],
    )
    op.create_index(
        "ix_calibration_recommendations_diagnostic_run_id",
        "calibration_recommendations",
        ["diagnostic_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_calibration_recommendations_diagnostic_run_id",
        table_name="calibration_recommendations",
    )
    op.drop_index(
        "ix_calibration_recommendations_strategy_profile_status",
        table_name="calibration_recommendations",
    )
    op.drop_index(
        "ix_calibration_recommendations_workspace_status_severity",
        table_name="calibration_recommendations",
    )
    op.drop_table("calibration_recommendations")
    op.drop_index(
        "ix_pattern_outcome_diagnostics_diagnostic_run_id",
        table_name="pattern_outcome_diagnostics",
    )
    op.drop_index(
        "ix_pattern_outcome_diagnostics_workspace_pattern_horizon",
        table_name="pattern_outcome_diagnostics",
    )
    op.drop_table("pattern_outcome_diagnostics")
    op.drop_index(
        "ix_strategy_profile_diagnostics_diagnostic_label",
        table_name="strategy_profile_diagnostics",
    )
    op.drop_index(
        "ix_strategy_profile_diagnostics_diagnostic_run_id",
        table_name="strategy_profile_diagnostics",
    )
    op.drop_index(
        "ix_strategy_profile_diagnostics_workspace_profile_horizon",
        table_name="strategy_profile_diagnostics",
    )
    op.drop_table("strategy_profile_diagnostics")
    op.drop_index(
        "ix_strategy_profile_diagnostic_runs_workspace_status",
        table_name="strategy_profile_diagnostic_runs",
    )
    op.drop_table("strategy_profile_diagnostic_runs")
