"""add strategy profile governance

Revision ID: 202605020900_profile_governance
Revises: 202604301900
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020900_profile_governance"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "strategy_profile_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_strategy_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("base_strategy_profile_key", sa.String(length=80), nullable=False),
        sa.Column("base_strategy_profile_version", sa.String(length=32), nullable=True),
        sa.Column("draft_key", sa.String(length=80), nullable=False),
        sa.Column("draft_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column(
            "proposed_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("validation_status", sa.String(length=32), nullable=False),
        sa.Column(
            "validation_errors_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "validation_warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "diff_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("simulation_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("diagnostic_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("promoted_strategy_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
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
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('draft', 'ready_for_review', 'approved', 'rejected', "
            "'promoted', 'archived')",
            name="strategy_profile_drafts_status_allowed",
        ),
        sa.CheckConstraint(
            "validation_status in ('not_validated', 'valid', 'valid_with_warnings', 'invalid')",
            name="strategy_profile_drafts_validation_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["base_strategy_profile_id"],
            ["strategy_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["diagnostic_run_id"],
            ["strategy_profile_diagnostic_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["promoted_strategy_profile_id"],
            ["strategy_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_strategy_profile_drafts_workspace_status",
        "strategy_profile_drafts",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_strategy_profile_drafts_key_version",
        "strategy_profile_drafts",
        ["draft_key", "draft_version"],
    )
    op.create_index(
        "ix_strategy_profile_drafts_base_strategy_profile_key",
        "strategy_profile_drafts",
        ["base_strategy_profile_key"],
    )
    op.create_index(
        "ix_strategy_profile_drafts_promoted_strategy_profile_id",
        "strategy_profile_drafts",
        ["promoted_strategy_profile_id"],
    )
    op.create_table(
        "strategy_profile_draft_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
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
            "event_type in ('created', 'validated', 'submitted_for_review', "
            "'approved', 'rejected', 'promoted', 'archived', 'note_added')",
            name="strategy_profile_draft_events_event_type_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_id"], ["strategy_profile_drafts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_strategy_profile_draft_events_draft_id",
        "strategy_profile_draft_events",
        ["draft_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_strategy_profile_draft_events_draft_id",
        table_name="strategy_profile_draft_events",
    )
    op.drop_table("strategy_profile_draft_events")
    op.drop_index(
        "ix_strategy_profile_drafts_promoted_strategy_profile_id",
        table_name="strategy_profile_drafts",
    )
    op.drop_index(
        "ix_strategy_profile_drafts_base_strategy_profile_key",
        table_name="strategy_profile_drafts",
    )
    op.drop_index("ix_strategy_profile_drafts_key_version", table_name="strategy_profile_drafts")
    op.drop_index(
        "ix_strategy_profile_drafts_workspace_status",
        table_name="strategy_profile_drafts",
    )
    op.drop_table("strategy_profile_drafts")
