"""add signal digest runs and items

Revision ID: 202605031400_signal_digests
Revises: 202605031300_market_memory_drift_attribution_scenario_merge
Create Date: 2026-05-03 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031400_signal_digests"
down_revision: str | Sequence[str] | None = (
    "202605031300_market_memory_drift_attribution_scenario_merge"
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_digest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("digest_version", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
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
            "section_counts_json",
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
            "digest_type in ('daily', 'session', 'custom_period', 'watchlist')",
            name="signal_digest_runs_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="signal_digest_runs_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_signal_digest_runs_workspace_type_created",
        "signal_digest_runs",
        ["workspace_id", "digest_type", "created_at"],
    )
    op.create_index(
        "ix_signal_digest_runs_period",
        "signal_digest_runs",
        ["period_start", "period_end"],
    )
    op.create_table(
        "signal_digest_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("digest_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("news_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
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
            "item_type in ('top_bias', 'no_signal', 'review_recommended', "
            "'data_quality_warning', 'outcome_update', 'news_context', 'pending_action', "
            "'conflict', 'stale_data', 'watch_condition')",
            name="signal_digest_items_type_allowed",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="signal_digest_items_priority_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["action_item_id"],
            ["reasoning_action_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["digest_run_id"],
            ["signal_digest_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["news_event_id"], ["news_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["outcome_id"], ["signal_outcomes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_signal_digest_items_run_type",
        "signal_digest_items",
        ["digest_run_id", "item_type"],
    )
    op.create_index(
        "ix_signal_digest_items_symbol_id",
        "signal_digest_items",
        ["symbol_id"],
    )
    op.create_index(
        "ix_signal_digest_items_signal_id",
        "signal_digest_items",
        ["signal_id"],
    )
    op.create_index(
        "ix_signal_digest_items_priority",
        "signal_digest_items",
        ["priority"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_digest_items_priority", table_name="signal_digest_items")
    op.drop_index("ix_signal_digest_items_signal_id", table_name="signal_digest_items")
    op.drop_index("ix_signal_digest_items_symbol_id", table_name="signal_digest_items")
    op.drop_index("ix_signal_digest_items_run_type", table_name="signal_digest_items")
    op.drop_table("signal_digest_items")
    op.drop_index("ix_signal_digest_runs_period", table_name="signal_digest_runs")
    op.drop_index(
        "ix_signal_digest_runs_workspace_type_created",
        table_name="signal_digest_runs",
    )
    op.drop_table("signal_digest_runs")
