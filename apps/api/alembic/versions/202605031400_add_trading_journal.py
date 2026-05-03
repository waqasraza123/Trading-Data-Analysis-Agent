"""add trading journal feedback loop

Revision ID: 202605031400_trading_journal
Revises: 202605031300_market_memory_drift_attribution_scenario_merge
Create Date: 2026-05-03 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031400_trading_journal"
down_revision: str | Sequence[str] | None = (
    "202605031300_market_memory_drift_attribution_scenario_merge"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("setup_context_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("chart_screenshot_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("decision_type", sa.String(length=32), nullable=False),
        sa.Column("confidence_before", sa.Numeric(5, 4), nullable=True),
        sa.Column("user_bias", sa.String(length=16), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=False),
        sa.Column(
            "tags_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
            "status in ('draft', 'saved', 'archived')",
            name="journal_entries_status_allowed",
        ),
        sa.CheckConstraint(
            "decision_type in ('observed', 'ignored', 'reviewed', 'paper_followed', "
            "'external_action_taken', 'no_action', 'uncertain')",
            name="journal_entries_decision_type_allowed",
        ),
        sa.CheckConstraint(
            "user_bias is null or user_bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="journal_entries_user_bias_allowed",
        ),
        sa.CheckConstraint(
            "confidence_before is null or (confidence_before >= 0 and confidence_before <= 1)",
            name="journal_entries_confidence_before_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["chart_screenshot_run_id"],
            ["chart_screenshot_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journal_entries_workspace_created_at",
        "journal_entries",
        ["workspace_id", "created_at"],
    )
    op.create_index("ix_journal_entries_signal_id", "journal_entries", ["signal_id"])
    op.create_index(
        "ix_journal_entries_analysis_run_id",
        "journal_entries",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_journal_entries_decision_type",
        "journal_entries",
        ["decision_type"],
    )

    op.create_table(
        "journal_entry_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_label", sa.String(length=40), nullable=True),
        sa.Column("reflection_label", sa.String(length=48), nullable=False),
        sa.Column("reflection_notes", sa.Text(), nullable=False),
        sa.Column(
            "lessons_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
            "reflection_label in ('aligned_with_observed_outcome', "
            "'conflicted_with_observed_outcome', 'inconclusive', "
            "'insufficient_outcome_data', 'needs_more_review')",
            name="journal_entry_reviews_reflection_label_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["outcome_id"], ["signal_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journal_entry_reviews_journal_entry_id",
        "journal_entry_reviews",
        ["journal_entry_id"],
    )
    op.create_index(
        "ix_journal_entry_reviews_reflection_label",
        "journal_entry_reviews",
        ["reflection_label"],
    )

    op.create_table(
        "journal_entry_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("journal_entry_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attachment_type", sa.String(length=32), nullable=False),
        sa.Column("reference_type", sa.String(length=80), nullable=False),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            "attachment_type in ('chart_screenshot', 'signal_report', 'audit_timeline', "
            "'external_note', 'dataset_reference')",
            name="journal_entry_attachments_type_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["journal_entry_id"],
            ["journal_entries.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journal_entry_attachments_journal_entry_id",
        "journal_entry_attachments",
        ["journal_entry_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_journal_entry_attachments_journal_entry_id",
        table_name="journal_entry_attachments",
    )
    op.drop_table("journal_entry_attachments")
    op.drop_index(
        "ix_journal_entry_reviews_reflection_label",
        table_name="journal_entry_reviews",
    )
    op.drop_index(
        "ix_journal_entry_reviews_journal_entry_id",
        table_name="journal_entry_reviews",
    )
    op.drop_table("journal_entry_reviews")
    op.drop_index("ix_journal_entries_decision_type", table_name="journal_entries")
    op.drop_index("ix_journal_entries_analysis_run_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_signal_id", table_name="journal_entries")
    op.drop_index("ix_journal_entries_workspace_created_at", table_name="journal_entries")
    op.drop_table("journal_entries")
