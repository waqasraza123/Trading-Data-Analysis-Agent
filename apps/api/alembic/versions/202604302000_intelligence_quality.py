"""add intelligence quality runs

Revision ID: 202604302000
Revises: 202604301900
Create Date: 2026-04-30 20:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604302000"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_quality_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quality_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("quality_label", sa.String(length=32), nullable=False),
        sa.Column("gate_version", sa.String(length=40), nullable=False),
        sa.Column("shadow_version", sa.String(length=40), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_type in ('analysis_run', 'signal', 'replay', 'screenshot_decision')",
            name="intelligence_quality_runs_source_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="intelligence_quality_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "quality_label in ('strong', 'acceptable', 'review_recommended', "
            "'inconsistent', 'insufficient_context')",
            name="intelligence_quality_runs_label_allowed",
        ),
        sa.CheckConstraint(
            "quality_score >= 0 and quality_score <= 1",
            name="intelligence_quality_runs_score_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_quality_runs_workspace_created",
        "intelligence_quality_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_intelligence_quality_runs_signal_id",
        "intelligence_quality_runs",
        ["signal_id"],
    )
    op.create_index(
        "ix_intelligence_quality_runs_analysis_run_id",
        "intelligence_quality_runs",
        ["analysis_run_id"],
    )
    op.create_table(
        "intelligence_quality_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quality_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("observed_value", sa.Text(), nullable=True),
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
            "finding_type in ('invariant_failure', 'contradiction', 'missing_artifact', "
            "'degraded_confidence', 'grounding_issue', 'shadow_disagreement', "
            "'safety_issue', 'review_recommendation')",
            name="intelligence_quality_findings_type_allowed",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name="intelligence_quality_findings_severity_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["quality_run_id"],
            ["intelligence_quality_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_quality_findings_run_id",
        "intelligence_quality_findings",
        ["quality_run_id"],
    )
    op.create_index(
        "ix_intelligence_quality_findings_severity",
        "intelligence_quality_findings",
        ["severity"],
    )
    op.create_index(
        "ix_intelligence_quality_findings_code",
        "intelligence_quality_findings",
        ["code"],
    )
    op.create_table(
        "shadow_classification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quality_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=False),
        sa.Column("strategy_profile_version", sa.String(length=32), nullable=False),
        sa.Column("classification_status", sa.String(length=32), nullable=False),
        sa.Column("bias", sa.String(length=16), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("confidence_label", sa.String(length=16), nullable=True),
        sa.Column("selected_candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agreement_with_final", sa.String(length=32), nullable=False),
        sa.Column("disagreement_reason", sa.Text(), nullable=True),
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
            "classification_status in ('signal', 'no_signal', 'unclear', 'insufficient_evidence')",
            name="shadow_classification_results_status_allowed",
        ),
        sa.CheckConstraint(
            "bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="shadow_classification_results_bias_allowed",
        ),
        sa.CheckConstraint(
            "confidence_score is null or (confidence_score >= 0 and confidence_score <= 1)",
            name="shadow_classification_results_confidence_range",
        ),
        sa.CheckConstraint(
            "confidence_label is null or confidence_label in ('low', 'medium', 'high', "
            "'very_high')",
            name="shadow_classification_results_confidence_label_allowed",
        ),
        sa.CheckConstraint(
            "agreement_with_final in ('agreed', 'disagreed_bias', 'disagreed_pattern', "
            "'disagreed_status', 'no_candidate', 'not_applicable')",
            name="shadow_classification_results_agreement_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["quality_run_id"],
            ["intelligence_quality_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["selected_candidate_id"],
            ["pattern_candidates.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shadow_classification_results_run_id",
        "shadow_classification_results",
        ["quality_run_id"],
    )
    op.create_index(
        "ix_shadow_classification_results_profile",
        "shadow_classification_results",
        ["strategy_profile_key"],
    )
    op.create_index(
        "ix_shadow_classification_results_agreement",
        "shadow_classification_results",
        ["agreement_with_final"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_shadow_classification_results_agreement",
        table_name="shadow_classification_results",
    )
    op.drop_index(
        "ix_shadow_classification_results_profile",
        table_name="shadow_classification_results",
    )
    op.drop_index(
        "ix_shadow_classification_results_run_id",
        table_name="shadow_classification_results",
    )
    op.drop_table("shadow_classification_results")
    op.drop_index(
        "ix_intelligence_quality_findings_code",
        table_name="intelligence_quality_findings",
    )
    op.drop_index(
        "ix_intelligence_quality_findings_severity",
        table_name="intelligence_quality_findings",
    )
    op.drop_index(
        "ix_intelligence_quality_findings_run_id",
        table_name="intelligence_quality_findings",
    )
    op.drop_table("intelligence_quality_findings")
    op.drop_index(
        "ix_intelligence_quality_runs_analysis_run_id",
        table_name="intelligence_quality_runs",
    )
    op.drop_index(
        "ix_intelligence_quality_runs_signal_id",
        table_name="intelligence_quality_runs",
    )
    op.drop_index(
        "ix_intelligence_quality_runs_workspace_created",
        table_name="intelligence_quality_runs",
    )
    op.drop_table("intelligence_quality_runs")
