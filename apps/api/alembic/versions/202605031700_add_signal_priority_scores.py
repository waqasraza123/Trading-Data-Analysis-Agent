"""add deterministic signal priority scores

Revision ID: 202605031700_signal_priority_scores
Revises: 202605031600_dashboard_digest_notifications_journal
Create Date: 2026-05-03 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031700_signal_priority_scores"
down_revision: str | Sequence[str] | None = "202605031600_dashboard_digest_notifications_journal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "signal_priority_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("priority_version", sa.String(length=32), nullable=False),
        sa.Column("priority_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("priority_label", sa.String(length=32), nullable=False),
        sa.Column("review_bucket", sa.String(length=48), nullable=False),
        sa.Column(
            "component_scores_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "penalties_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "boosters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "reasons_json",
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
            "priority_score >= 0 and priority_score <= 1",
            name="signal_priority_score_range",
        ),
        sa.CheckConstraint(
            "priority_label in ('urgent_review', 'high', 'medium', 'low', 'avoid', 'stale')",
            name="signal_priority_label_allowed",
        ),
        sa.CheckConstraint(
            "review_bucket in ('high_quality_context', 'needs_confirmation', 'conflicted', "
            "'avoid_or_no_directional_signal', 'stale_or_data_issue', 'review_required')",
            name="signal_priority_review_bucket_allowed",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "signal_id",
            "priority_version",
            name="uq_signal_priority_signal_version",
        ),
    )
    op.create_index(
        "ix_signal_priority_workspace_label",
        "signal_priority_scores",
        ["workspace_id", "priority_label"],
    )
    op.create_index(
        "ix_signal_priority_workspace_bucket",
        "signal_priority_scores",
        ["workspace_id", "review_bucket"],
    )
    op.create_index(
        "ix_signal_priority_workspace_symbol_timeframe",
        "signal_priority_scores",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_signal_priority_signal_id",
        "signal_priority_scores",
        ["signal_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_priority_signal_id", table_name="signal_priority_scores")
    op.drop_index(
        "ix_signal_priority_workspace_symbol_timeframe",
        table_name="signal_priority_scores",
    )
    op.drop_index("ix_signal_priority_workspace_bucket", table_name="signal_priority_scores")
    op.drop_index("ix_signal_priority_workspace_label", table_name="signal_priority_scores")
    op.drop_table("signal_priority_scores")
