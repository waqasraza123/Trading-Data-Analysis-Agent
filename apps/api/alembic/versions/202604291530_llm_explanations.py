"""add grounded llm explanations

Revision ID: 202604291530
Revises: 202604291430
Create Date: 2026-04-29 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291530"
down_revision: str | tuple[str, str] | None = "202604291430"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("prompt_version", sa.String(length=40), nullable=False),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("output_text", sa.Text(), nullable=False),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column(
            "blocked_terms_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("grounding_status", sa.String(length=20), nullable=False),
        sa.Column(
            "grounding_issues_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("tokens_input", sa.Integer(), nullable=True),
        sa.Column("tokens_output", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(precision=16, scale=6), nullable=True),
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
            "safety_status in ('passed', 'blocked', 'fallback_used', 'failed')",
            name=op.f("ck_llm_explanations_llm_explanation_safety_status_allowed"),
        ),
        sa.CheckConstraint(
            "grounding_status in ('grounded', 'questionable', 'failed', 'not_checked')",
            name=op.f("ck_llm_explanations_llm_explanation_grounding_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_llm_explanations_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_llm_explanations_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_llm_explanations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_explanations")),
        sa.UniqueConstraint(
            "signal_id",
            "provider",
            "model",
            "prompt_version",
            name="uq_llm_explanations_signal_id_provider_model_prompt_version",
        ),
    )
    op.create_index("ix_llm_explanations_signal_id", "llm_explanations", ["signal_id"])
    op.create_index(
        "ix_llm_explanations_analysis_run_id",
        "llm_explanations",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_llm_explanations_workspace_created",
        "llm_explanations",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_explanations_workspace_created", table_name="llm_explanations")
    op.drop_index("ix_llm_explanations_analysis_run_id", table_name="llm_explanations")
    op.drop_index("ix_llm_explanations_signal_id", table_name="llm_explanations")
    op.drop_table("llm_explanations")
