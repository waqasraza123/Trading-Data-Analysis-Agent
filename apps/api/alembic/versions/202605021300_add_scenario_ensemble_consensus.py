"""add scenario ensemble consensus

Revision ID: 202605021300_scenario_ensembles
Revises: 202605021250_intelligence_dataset_exports
Create Date: 2026-05-02 13:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021300_scenario_ensembles"
down_revision: str | Sequence[str] | None = "202605021250_intelligence_dataset_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_ensemble_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("ensemble_version", sa.String(length=40), nullable=False),
        sa.Column(
            "requested_providers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "requested_models_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "reasoning_run_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("consensus_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("consensus_label", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column("grounding_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed', "
            "'provider_not_configured')",
            name="scenario_ensemble_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "consensus_label in ('strong_agreement', 'partial_agreement', 'disagreement', "
            "'insufficient_context', 'failed')",
            name="scenario_ensemble_runs_consensus_label_allowed",
        ),
        sa.CheckConstraint(
            "consensus_score >= 0 and consensus_score <= 1",
            name="scenario_ensemble_runs_consensus_score_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenario_ensemble_runs_workspace_signal",
        "scenario_ensemble_runs",
        ["workspace_id", "signal_id"],
    )
    op.create_index(
        "ix_scenario_ensemble_runs_consensus_label",
        "scenario_ensemble_runs",
        ["consensus_label"],
    )
    op.create_table(
        "scenario_ensemble_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ensemble_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "scenario_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "suggested_actions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column("grounding_status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('completed', 'failed', 'blocked', 'fallback_used', "
            "'provider_not_configured')",
            name="scenario_ensemble_items_status_allowed",
        ),
        sa.ForeignKeyConstraint(["ensemble_run_id"], ["scenario_ensemble_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reasoning_run_id"], ["llm_reasoning_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenario_ensemble_items_run_id",
        "scenario_ensemble_items",
        ["ensemble_run_id"],
    )
    op.create_table(
        "scenario_consensus_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ensemble_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_type", sa.String(length=40), nullable=False),
        sa.Column("agreement_count", sa.Integer(), nullable=False),
        sa.Column("disagreement_count", sa.Integer(), nullable=False),
        sa.Column(
            "possibility_labels_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
        sa.Column("consensus_label", sa.String(length=32), nullable=False),
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
            "consensus_label in ('strong_agreement', 'partial_agreement', 'disagreement', "
            "'insufficient_context', 'failed')",
            name="scenario_consensus_results_consensus_label_allowed",
        ),
        sa.CheckConstraint(
            "agreement_count >= 0 and disagreement_count >= 0",
            name="scenario_consensus_results_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["ensemble_run_id"], ["scenario_ensemble_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scenario_consensus_results_run_id",
        "scenario_consensus_results",
        ["ensemble_run_id"],
    )
    op.create_index(
        "ix_scenario_consensus_results_scenario_type",
        "scenario_consensus_results",
        ["scenario_type"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scenario_consensus_results_scenario_type",
        table_name="scenario_consensus_results",
    )
    op.drop_index(
        "ix_scenario_consensus_results_run_id",
        table_name="scenario_consensus_results",
    )
    op.drop_table("scenario_consensus_results")
    op.drop_index("ix_scenario_ensemble_items_run_id", table_name="scenario_ensemble_items")
    op.drop_table("scenario_ensemble_items")
    op.drop_index(
        "ix_scenario_ensemble_runs_consensus_label",
        table_name="scenario_ensemble_runs",
    )
    op.drop_index(
        "ix_scenario_ensemble_runs_workspace_signal",
        table_name="scenario_ensemble_runs",
    )
    op.drop_table("scenario_ensemble_runs")
