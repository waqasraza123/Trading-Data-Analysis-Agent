"""add ai intelligence analyst records

Revision ID: 202604301700
Revises: 202604301600
Create Date: 2026-04-30 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604301700"
down_revision: str | Sequence[str] | None = "202604301600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_intelligence_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_type", sa.String(length=32), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "subject_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', "
            "'screenshot_decision')",
            name="ai_intelligence_runs_subject_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'blocked', 'fallback_used', "
            "'provider_not_configured', 'failed')",
            name="ai_intelligence_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used', 'failed')",
            name="ai_intelligence_runs_safety_status_allowed",
        ),
        sa.CheckConstraint(
            "grounding_status in ('grounded', 'questionable', 'failed', 'not_checked')",
            name="ai_intelligence_runs_grounding_status_allowed",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outcome_id"], ["signal_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_intelligence_runs_workspace_created",
        "ai_intelligence_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_ai_intelligence_runs_subject",
        "ai_intelligence_runs",
        ["subject_type", "subject_id"],
    )
    op.create_index(
        "ix_ai_intelligence_runs_signal_created",
        "ai_intelligence_runs",
        ["signal_id", "created_at"],
    )
    op.create_index(
        "ix_ai_intelligence_runs_analysis_created",
        "ai_intelligence_runs",
        ["analysis_run_id", "created_at"],
    )
    op.create_table(
        "ai_intelligence_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("insight_type", sa.String(length=48), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "evidence_refs_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "limitations_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "safe_follow_up_actions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "insight_type in ('evidence_consistency', 'confidence_alignment', "
            "'outcome_context', 'diagnostic_context', 'news_context', 'action_plan_context', "
            "'data_gap', 'risk_context', 'human_review_context', 'general_context')",
            name="ai_intelligence_insights_type_allowed",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high')",
            name="ai_intelligence_insights_severity_allowed",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["ai_intelligence_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_intelligence_insights_run_id", "ai_intelligence_insights", ["run_id"])
    op.create_index(
        "ix_ai_intelligence_insights_workspace_type",
        "ai_intelligence_insights",
        ["workspace_id", "insight_type"],
    )
    op.create_table(
        "ai_intelligence_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("insight_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("support_status", sa.String(length=16), nullable=False),
        sa.Column(
            "evidence_refs_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "support_status in ('supported', 'partial', 'unsupported')",
            name="ai_intelligence_claims_support_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["insight_id"],
            ["ai_intelligence_insights.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["ai_intelligence_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_intelligence_claims_run_id", "ai_intelligence_claims", ["run_id"])
    op.create_index(
        "ix_ai_intelligence_claims_insight_id",
        "ai_intelligence_claims",
        ["insight_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_intelligence_claims_insight_id", table_name="ai_intelligence_claims")
    op.drop_index("ix_ai_intelligence_claims_run_id", table_name="ai_intelligence_claims")
    op.drop_table("ai_intelligence_claims")
    op.drop_index(
        "ix_ai_intelligence_insights_workspace_type",
        table_name="ai_intelligence_insights",
    )
    op.drop_index("ix_ai_intelligence_insights_run_id", table_name="ai_intelligence_insights")
    op.drop_table("ai_intelligence_insights")
    op.drop_index(
        "ix_ai_intelligence_runs_analysis_created",
        table_name="ai_intelligence_runs",
    )
    op.drop_index("ix_ai_intelligence_runs_signal_created", table_name="ai_intelligence_runs")
    op.drop_index("ix_ai_intelligence_runs_subject", table_name="ai_intelligence_runs")
    op.drop_index(
        "ix_ai_intelligence_runs_workspace_created",
        table_name="ai_intelligence_runs",
    )
    op.drop_table("ai_intelligence_runs")
