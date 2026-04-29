"""create deterministic explanations

Revision ID: 202604291200
Revises: 202604291130
Create Date: 2026-04-29 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291200"
down_revision: str | None = "202604291130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deterministic_explanations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_version", sa.String(length=40), nullable=False),
        sa.Column("explanation_type", sa.String(length=32), nullable=False),
        sa.Column("short_summary", sa.Text(), nullable=False),
        sa.Column("market_behavior", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=False),
        sa.Column("confidence_summary", sa.Text(), nullable=False),
        sa.Column("risk_summary", sa.Text(), nullable=False),
        sa.Column("no_signal_summary", sa.Text(), nullable=True),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column(
            "source_snapshot_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("safety_status", sa.String(length=32), nullable=False),
        sa.Column(
            "blocked_terms_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
            "explanation_type in ('deterministic_signal', 'deterministic_no_signal')",
            name=op.f(
                "ck_deterministic_explanations_deterministic_explanation_type_allowed"
            ),
        ),
        sa.CheckConstraint(
            "safety_status in ('passed', 'blocked', 'fallback_used')",
            name=op.f(
                "ck_deterministic_explanations_deterministic_explanation_safety_status_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_deterministic_explanations_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_deterministic_explanations_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_deterministic_explanations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_deterministic_explanations")),
        sa.UniqueConstraint("signal_id", name="uq_deterministic_explanations_signal_id"),
    )
    op.create_index(
        "ix_deterministic_explanations_signal_id",
        "deterministic_explanations",
        ["signal_id"],
        unique=False,
    )
    op.create_index(
        "ix_deterministic_explanations_analysis_run_id",
        "deterministic_explanations",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_deterministic_explanations_workspace_created",
        "deterministic_explanations",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_deterministic_explanations_workspace_created",
        table_name="deterministic_explanations",
    )
    op.drop_index(
        "ix_deterministic_explanations_analysis_run_id",
        table_name="deterministic_explanations",
    )
    op.drop_index(
        "ix_deterministic_explanations_signal_id",
        table_name="deterministic_explanations",
    )
    op.drop_table("deterministic_explanations")
