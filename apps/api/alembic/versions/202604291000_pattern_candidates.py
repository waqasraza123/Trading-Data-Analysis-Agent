"""create pattern candidates

Revision ID: 202604291000
Revises: 202604290930
Create Date: 2026-04-29 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291000"
down_revision: str | None = "202604290930"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pattern_candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column("bias", sa.String(length=16), nullable=False),
        sa.Column("strength_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("is_selected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "evidence_json",
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
        sa.Column(
            "metrics_json",
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
            "bias in ('bullish', 'bearish', 'neutral')",
            name=op.f("ck_pattern_candidates_pattern_candidate_bias_allowed"),
        ),
        sa.CheckConstraint(
            "strength_score >= 0 and strength_score <= 1",
            name=op.f("ck_pattern_candidates_pattern_candidate_strength_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_pattern_candidates_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_pattern_candidates_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_pattern_candidates_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pattern_candidates")),
    )
    op.create_index(
        "ix_pattern_candidates_analysis_run_id",
        "pattern_candidates",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_pattern_candidates_workspace_symbol_type",
        "pattern_candidates",
        ["workspace_id", "symbol_id", "pattern_type"],
        unique=False,
    )
    op.create_index(
        "ix_pattern_candidates_selected",
        "pattern_candidates",
        ["analysis_run_id", "is_selected"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_pattern_candidates_selected", table_name="pattern_candidates")
    op.drop_index(
        "ix_pattern_candidates_workspace_symbol_type",
        table_name="pattern_candidates",
    )
    op.drop_index("ix_pattern_candidates_analysis_run_id", table_name="pattern_candidates")
    op.drop_table("pattern_candidates")
