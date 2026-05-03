from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260502_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "safety_policy_sets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_policy_sets_key_version_status", "safety_policy_sets", ["key", "version", "status"])
    op.create_table(
        "safety_policy_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("policy_set_key", sa.String(length=120), nullable=False),
        sa.Column("policy_set_version", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=True),
        sa.Column("evaluation_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("safety_status", sa.String(length=40), nullable=False),
        sa.Column("input_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("findings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("redacted_output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_safety_policy_evaluations_workspace_created_at", "safety_policy_evaluations", ["workspace_id", "created_at"])
    op.create_index("ix_safety_policy_evaluations_source_type_source_id", "safety_policy_evaluations", ["source_type", "source_id"])
    op.create_index("ix_safety_policy_evaluations_safety_status", "safety_policy_evaluations", ["safety_status"])


def downgrade() -> None:
    op.drop_index("ix_safety_policy_evaluations_safety_status", table_name="safety_policy_evaluations")
    op.drop_index("ix_safety_policy_evaluations_source_type_source_id", table_name="safety_policy_evaluations")
    op.drop_index("ix_safety_policy_evaluations_workspace_created_at", table_name="safety_policy_evaluations")
    op.drop_table("safety_policy_evaluations")
    op.drop_index("ix_safety_policy_sets_key_version_status", table_name="safety_policy_sets")
    op.drop_table("safety_policy_sets")

