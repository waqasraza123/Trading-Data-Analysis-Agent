"""add decision readiness assessments

Revision ID: 202605021100
Revises: 202604301900
Create Date: 2026-05-02 11:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605021100"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "decision_readiness_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assessment_version", sa.String(length=40), nullable=False),
        sa.Column("readiness_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("readiness_label", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "required_checks_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "optional_checks_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "blockers_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "next_steps_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
            "source_type in ('signal', 'analysis_run', 'reasoning_run', 'outcome', 'screenshot_decision')",
            name=op.f("ck_decision_readiness_assessments_decision_readiness_source_type_allowed"),
        ),
        sa.CheckConstraint(
            "readiness_label in ('ready', 'review_recommended', 'blocked', 'insufficient_context')",
            name=op.f("ck_decision_readiness_assessments_decision_readiness_label_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('completed', 'failed')",
            name=op.f("ck_decision_readiness_assessments_decision_readiness_status_allowed"),
        ),
        sa.CheckConstraint(
            "readiness_score >= 0 and readiness_score <= 1",
            name=op.f("ck_decision_readiness_assessments_decision_readiness_score_range"),
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "source_id",
            "assessment_version",
            name=op.f("uq_decision_readiness_source_version"),
        ),
    )
    op.create_index(
        "ix_decision_readiness_analysis_run_id",
        "decision_readiness_assessments",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_readiness_signal_id",
        "decision_readiness_assessments",
        ["signal_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_readiness_source",
        "decision_readiness_assessments",
        ["source_type", "source_id"],
        unique=False,
    )
    op.create_index(
        "ix_decision_readiness_workspace_label",
        "decision_readiness_assessments",
        ["workspace_id", "readiness_label"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_decision_readiness_workspace_label",
        table_name="decision_readiness_assessments",
    )
    op.drop_index(
        "ix_decision_readiness_source",
        table_name="decision_readiness_assessments",
    )
    op.drop_index(
        "ix_decision_readiness_signal_id",
        table_name="decision_readiness_assessments",
    )
    op.drop_index(
        "ix_decision_readiness_analysis_run_id",
        table_name="decision_readiness_assessments",
    )
    op.drop_table("decision_readiness_assessments")
