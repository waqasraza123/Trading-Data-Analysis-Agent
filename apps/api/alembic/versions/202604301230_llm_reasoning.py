"""add llm scenario reasoning tables

Revision ID: 202604301230
Revises: 202604301030
Create Date: 2026-04-30 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301230"
down_revision: str | tuple[str, str] | None = "202604301030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_reasoning_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column("reasoning_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "input_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_text", sa.Text(), nullable=True),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column("grounding_status", sa.String(length=20), nullable=False),
        sa.Column(
            "blocked_terms_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "grounding_issues_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=16, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
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
            "grounding_status in ('grounded', 'questionable', 'failed', 'not_checked')",
            name=op.f("ck_llm_reasoning_runs_llm_reasoning_runs_grounding_status_allowed"),
        ),
        sa.CheckConstraint(
            "reasoning_type in ('next_scenarios', 'outcome_interpretation', "
            "'evidence_review', 'risk_review', 'human_review_assist')",
            name=op.f("ck_llm_reasoning_runs_llm_reasoning_runs_reasoning_type_allowed"),
        ),
        sa.CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used', 'failed')",
            name=op.f("ck_llm_reasoning_runs_llm_reasoning_runs_safety_status_allowed"),
        ),
        sa.CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'outcome', 'screenshot_decision', 'replay')",
            name=op.f("ck_llm_reasoning_runs_llm_reasoning_runs_source_type_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'failed', 'blocked', 'fallback_used', "
            "'provider_not_configured')",
            name=op.f("ck_llm_reasoning_runs_llm_reasoning_runs_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_llm_reasoning_runs_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["outcome_id"],
            ["signal_outcomes.id"],
            name=op.f("fk_llm_reasoning_runs_outcome_id_signal_outcomes"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_llm_reasoning_runs_signal_id_signals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_llm_reasoning_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_reasoning_runs")),
    )
    op.create_index(
        "ix_llm_reasoning_runs_workspace_created",
        "llm_reasoning_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_llm_reasoning_runs_signal_reasoning",
        "llm_reasoning_runs",
        ["signal_id", "reasoning_type"],
    )
    op.create_index(
        "ix_llm_reasoning_runs_analysis_reasoning",
        "llm_reasoning_runs",
        ["analysis_run_id", "reasoning_type"],
    )
    op.create_table(
        "scenario_hypotheses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scenario_type", sa.String(length=40), nullable=False),
        sa.Column("scenario_label", sa.String(length=300), nullable=False),
        sa.Column("possibility_label", sa.String(length=16), nullable=False),
        sa.Column(
            "supporting_evidence_json",
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
        sa.Column("outcome_history_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "next_observations_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "suggested_backend_actions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "risk_notes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "possibility_label in ('low', 'medium', 'high', 'uncertain')",
            name=op.f("ck_scenario_hypotheses_scenario_hypotheses_possibility_label_allowed"),
        ),
        sa.CheckConstraint(
            "scenario_type in ('continuation', 'reversal', 'consolidation', "
            "'volatility_expansion', 'fakeout_risk', 'event_driven_volatility', "
            "'insufficient_context')",
            name=op.f("ck_scenario_hypotheses_scenario_hypotheses_scenario_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_scenario_hypotheses_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            name=op.f("fk_scenario_hypotheses_reasoning_run_id_llm_reasoning_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_scenario_hypotheses_signal_id_signals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_scenario_hypotheses_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scenario_hypotheses")),
    )
    op.create_index(
        "ix_scenario_hypotheses_reasoning_run_id",
        "scenario_hypotheses",
        ["reasoning_run_id"],
    )
    op.create_index(
        "ix_scenario_hypotheses_signal_id",
        "scenario_hypotheses",
        ["signal_id"],
    )
    op.create_index(
        "ix_scenario_hypotheses_scenario_type",
        "scenario_hypotheses",
        ["scenario_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_scenario_hypotheses_scenario_type", table_name="scenario_hypotheses")
    op.drop_index("ix_scenario_hypotheses_signal_id", table_name="scenario_hypotheses")
    op.drop_index("ix_scenario_hypotheses_reasoning_run_id", table_name="scenario_hypotheses")
    op.drop_table("scenario_hypotheses")
    op.drop_index(
        "ix_llm_reasoning_runs_analysis_reasoning",
        table_name="llm_reasoning_runs",
    )
    op.drop_index("ix_llm_reasoning_runs_signal_reasoning", table_name="llm_reasoning_runs")
    op.drop_index("ix_llm_reasoning_runs_workspace_created", table_name="llm_reasoning_runs")
    op.drop_table("llm_reasoning_runs")
