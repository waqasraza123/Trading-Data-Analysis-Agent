"""add daily brief runs and items

Revision ID: 202605031900_daily_briefs
Revises: 202605031900_notification_event_inbox
Create Date: 2026-05-03 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031900_daily_briefs"
down_revision: str | Sequence[str] | None = "202605031900_notification_event_inbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "daily_brief_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("brief_type", sa.String(length=32), nullable=False),
        sa.Column("brief_version", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "sections_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
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
            "brief_type in ('daily', 'session', 'intraday', 'watchlist', 'custom_period')",
            name="daily_brief_runs_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="daily_brief_runs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["digest_id"], ["signal_digest_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["watchlist_id"], ["market_watchlists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_brief_runs_workspace_type_generated",
        "daily_brief_runs",
        ["workspace_id", "brief_type", "generated_at"],
    )
    op.create_index(
        "ix_daily_brief_runs_watchlist_generated",
        "daily_brief_runs",
        ["watchlist_id", "generated_at"],
    )
    op.create_table(
        "daily_brief_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brief_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("setup_context_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
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
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "item_type in ('review_first', 'needs_confirmation', 'avoid_condition', "
            "'stale_data', 'outcome_update', 'watch_next', 'pending_action', "
            "'market_context', 'data_quality_issue', 'journal_follow_up')",
            name="daily_brief_items_type_allowed",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="daily_brief_items_priority_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["action_item_id"], ["reasoning_action_items.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["brief_run_id"], ["daily_brief_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outcome_id"], ["signal_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["setup_context_id"], ["setup_contexts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_daily_brief_items_run_type",
        "daily_brief_items",
        ["brief_run_id", "item_type"],
    )
    op.create_index(
        "ix_daily_brief_items_workspace_priority",
        "daily_brief_items",
        ["workspace_id", "priority"],
    )
    op.create_index(
        "ix_daily_brief_items_signal_id",
        "daily_brief_items",
        ["signal_id"],
    )
    op.create_index(
        "ix_daily_brief_items_symbol_id",
        "daily_brief_items",
        ["symbol_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_daily_brief_items_symbol_id", table_name="daily_brief_items")
    op.drop_index("ix_daily_brief_items_signal_id", table_name="daily_brief_items")
    op.drop_index("ix_daily_brief_items_workspace_priority", table_name="daily_brief_items")
    op.drop_index("ix_daily_brief_items_run_type", table_name="daily_brief_items")
    op.drop_table("daily_brief_items")
    op.drop_index("ix_daily_brief_runs_watchlist_generated", table_name="daily_brief_runs")
    op.drop_index("ix_daily_brief_runs_workspace_type_generated", table_name="daily_brief_runs")
    op.drop_table("daily_brief_runs")
