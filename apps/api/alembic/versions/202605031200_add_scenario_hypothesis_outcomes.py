"""add scenario hypothesis outcomes

Revision ID: 202605031200_scenario_hypothesis_outcomes
Revises: 202605031100_context_validation_recovery_merge
Create Date: 2026-05-03 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031200_scenario_hypothesis_outcomes"
down_revision: str | Sequence[str] | None = "202605031100_context_validation_recovery_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_hypothesis_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_hypothesis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("horizon_minutes", sa.Integer(), nullable=True),
        sa.Column("evaluation_version", sa.String(length=32), nullable=False),
        sa.Column("scenario_type", sa.String(length=40), nullable=False),
        sa.Column("possibility_label", sa.String(length=16), nullable=False),
        sa.Column("evaluation_status", sa.String(length=32), nullable=False),
        sa.Column("support_label", sa.String(length=32), nullable=False),
        sa.Column("support_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("matched_outcome_label", sa.String(length=40), nullable=True),
        sa.Column(
            "matched_evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "conflicting_evidence_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
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
            "evaluation_status in ('evaluated', 'insufficient_outcome_data', "
            "'not_applicable', 'failed')",
            name="scenario_hypothesis_outcomes_evaluation_status_allowed",
        ),
        sa.CheckConstraint(
            "support_label in ('supported', 'partially_supported', 'contradicted', "
            "'inconclusive', 'not_applicable')",
            name="scenario_hypothesis_outcomes_support_label_allowed",
        ),
        sa.CheckConstraint(
            "support_score >= 0 and support_score <= 1",
            name="scenario_hypothesis_outcomes_support_score_range",
        ),
        sa.CheckConstraint(
            "horizon_minutes is null or horizon_minutes > 0",
            name="scenario_hypothesis_outcomes_horizon_positive",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outcome_id"], ["signal_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_hypothesis_id"],
            ["scenario_hypotheses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scenario_hypothesis_id",
            "horizon_minutes",
            "evaluation_version",
            name="uq_scenario_hypothesis_outcomes_hypothesis_horizon_version",
        ),
    )
    op.create_index(
        "ix_scenario_hypothesis_outcomes_hypothesis_id",
        "scenario_hypothesis_outcomes",
        ["scenario_hypothesis_id"],
    )
    op.create_index(
        "ix_scenario_hypothesis_outcomes_reasoning_run_id",
        "scenario_hypothesis_outcomes",
        ["reasoning_run_id"],
    )
    op.create_index(
        "ix_scenario_hypothesis_outcomes_signal_id",
        "scenario_hypothesis_outcomes",
        ["signal_id"],
    )
    op.create_index(
        "ix_scenario_hypothesis_outcomes_scenario_type",
        "scenario_hypothesis_outcomes",
        ["scenario_type"],
    )
    op.create_index(
        "ix_scenario_hypothesis_outcomes_support_label",
        "scenario_hypothesis_outcomes",
        ["support_label"],
    )
    op.create_table(
        "scenario_outcome_summary_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("evaluated_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("supported_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "partially_supported_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("contradicted_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("inconclusive_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
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
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="scenario_outcome_summary_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "evaluated_count >= 0 and supported_count >= 0 and partially_supported_count >= 0 "
            "and contradicted_count >= 0 and inconclusive_count >= 0",
            name="scenario_outcome_summary_runs_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenario_outcome_summary_runs_workspace_created",
        "scenario_outcome_summary_runs",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scenario_outcome_summary_runs_workspace_created",
        table_name="scenario_outcome_summary_runs",
    )
    op.drop_table("scenario_outcome_summary_runs")
    op.drop_index(
        "ix_scenario_hypothesis_outcomes_support_label",
        table_name="scenario_hypothesis_outcomes",
    )
    op.drop_index(
        "ix_scenario_hypothesis_outcomes_scenario_type",
        table_name="scenario_hypothesis_outcomes",
    )
    op.drop_index(
        "ix_scenario_hypothesis_outcomes_signal_id",
        table_name="scenario_hypothesis_outcomes",
    )
    op.drop_index(
        "ix_scenario_hypothesis_outcomes_reasoning_run_id",
        table_name="scenario_hypothesis_outcomes",
    )
    op.drop_index(
        "ix_scenario_hypothesis_outcomes_hypothesis_id",
        table_name="scenario_hypothesis_outcomes",
    )
    op.drop_table("scenario_hypothesis_outcomes")
