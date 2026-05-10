"""add explanation comparison

Revision ID: 202605031000_explanation_comparison
Revises: 202605021500_scalable_engines_merge
Create Date: 2026-05-03 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031000_explanation_comparison"
down_revision: str | Sequence[str] | None = "202605021500_scalable_engines_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "explanation_comparison_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("comparison_version", sa.String(length=40), nullable=False),
        sa.Column("deterministic_explanation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("llm_explanation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("alignment_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("alignment_label", sa.String(length=32), nullable=False),
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
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="explanation_comparison_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "alignment_label in ('aligned', 'mostly_aligned', 'mixed', 'conflicting', "
            "'insufficient_context')",
            name="explanation_comparison_runs_alignment_label_allowed",
        ),
        sa.CheckConstraint(
            "alignment_score >= 0 and alignment_score <= 1",
            name="explanation_comparison_runs_score_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["deterministic_explanation_id"],
            ["deterministic_explanations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["llm_explanation_id"],
            ["llm_explanations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_explanation_comparison_runs_workspace_signal",
        "explanation_comparison_runs",
        ["workspace_id", "signal_id"],
    )
    op.create_index(
        "ix_explanation_comparison_runs_alignment_label",
        "explanation_comparison_runs",
        ["alignment_label"],
    )
    op.create_table(
        "explanation_comparison_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comparison_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.String(length=160), nullable=True),
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
            "finding_type in ('missing_context', 'contradiction', 'unsupported_claim', "
            "'omitted_risk', 'unsafe_language', 'causation_language', "
            "'explanation_mismatch')",
            name="explanation_comparison_findings_type_allowed",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="explanation_comparison_findings_severity_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["comparison_run_id"],
            ["explanation_comparison_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_explanation_comparison_findings_run_id",
        "explanation_comparison_findings",
        ["comparison_run_id"],
    )
    op.create_index(
        "ix_explanation_comparison_findings_severity_code",
        "explanation_comparison_findings",
        ["severity", "code"],
    )


def downgrade() -> None:
    op.drop_table("explanation_comparison_findings")
    op.drop_table("explanation_comparison_runs")
