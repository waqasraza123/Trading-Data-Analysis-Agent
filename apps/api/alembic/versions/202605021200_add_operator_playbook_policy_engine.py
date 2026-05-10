"""add operator playbook policy engine

Revision ID: 202605021220_operator_playbook_policy_engine
Revises: 202605021100_decision_readiness_assessments, 202605021110_strategy_profile_simulations
Create Date: 2026-05-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021220_operator_playbook_policy_engine"
down_revision: str | Sequence[str] | None = (
    "202605021100_decision_readiness_assessments",
    "202605021110_strategy_profile_simulations",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operator_playbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "trigger_rules_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "recommended_actions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("severity", sa.String(length=16), nullable=False),
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
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name=op.f("ck_operator_playbooks_operator_playbooks_severity_allowed"),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", "version", name=op.f("uq_operator_playbooks_key_version")),
    )
    op.create_index("ix_operator_playbooks_active", "operator_playbooks", ["is_active"])
    op.create_index("ix_operator_playbooks_key", "operator_playbooks", ["key"])
    op.create_table(
        "operator_playbook_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("playbook_key", sa.String(length=120), nullable=False),
        sa.Column("playbook_version", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("matched", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "recommended_actions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_json",
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
            "source_type in ('signal', 'analysis_run', 'quality_run', 'readiness_assessment', "
            "'outcome', 'reasoning_run', 'chart_screenshot_run', 'action_plan')",
            name=op.f(
                "ck_operator_playbook_evaluations_operator_playbook_evaluations_source_type_allowed"
            ),
        ),
        sa.CheckConstraint(
            "status in ('completed', 'failed')",
            name=op.f(
                "ck_operator_playbook_evaluations_operator_playbook_evaluations_status_allowed"
            ),
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name=op.f(
                "ck_operator_playbook_evaluations_operator_playbook_evaluations_severity_allowed"
            ),
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "playbook_key",
            "playbook_version",
            "source_type",
            "source_id",
            name=op.f("uq_operator_playbook_evaluations_playbook_source"),
        ),
    )
    op.create_index(
        "ix_operator_playbook_evaluations_matched_severity",
        "operator_playbook_evaluations",
        ["matched", "severity"],
    )
    op.create_index(
        "ix_operator_playbook_evaluations_source",
        "operator_playbook_evaluations",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_operator_playbook_evaluations_workspace_playbook",
        "operator_playbook_evaluations",
        ["workspace_id", "playbook_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operator_playbook_evaluations_workspace_playbook",
        table_name="operator_playbook_evaluations",
    )
    op.drop_index(
        "ix_operator_playbook_evaluations_source",
        table_name="operator_playbook_evaluations",
    )
    op.drop_index(
        "ix_operator_playbook_evaluations_matched_severity",
        table_name="operator_playbook_evaluations",
    )
    op.drop_table("operator_playbook_evaluations")
    op.drop_index("ix_operator_playbooks_key", table_name="operator_playbooks")
    op.drop_index("ix_operator_playbooks_active", table_name="operator_playbooks")
    op.drop_table("operator_playbooks")
