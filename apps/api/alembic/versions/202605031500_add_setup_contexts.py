"""add actionable setup contexts

Revision ID: 202605031500_setup_contexts
Revises: notification delivery, signal digests, trading journal
Create Date: 2026-05-03 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031500_setup_contexts"
down_revision: str | Sequence[str] | None = (
    "202605031400_notification_delivery_engine",
    "202605031400_signal_digests",
    "202605031400_trading_journal",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "setup_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("context_version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("directional_bias", sa.String(length=16), nullable=False),
        sa.Column("setup_quality_label", sa.String(length=32), nullable=False),
        sa.Column("setup_quality_score", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "invalidation_context_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "observation_zones_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "target_context_zones_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "wait_conditions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "avoid_reasons_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "timeframe_agreement_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "data_quality_warnings_json",
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
            "next_observations_json",
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
            "status in ('completed', 'completed_with_warnings', 'insufficient_context', 'failed')",
            name="setup_contexts_status_allowed",
        ),
        sa.CheckConstraint(
            "directional_bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="setup_contexts_directional_bias_allowed",
        ),
        sa.CheckConstraint(
            "setup_quality_label in ('strong_context', 'acceptable_context', 'mixed_context', "
            "'review_required', 'avoid_condition', 'insufficient_context')",
            name="setup_contexts_quality_label_allowed",
        ),
        sa.CheckConstraint(
            "setup_quality_score >= 0 and setup_quality_score <= 1",
            name="setup_contexts_quality_score_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("signal_id", "context_version", name="uq_setup_contexts_signal_version"),
    )
    op.create_index(
        "ix_setup_contexts_workspace_symbol_timeframe",
        "setup_contexts",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index("ix_setup_contexts_signal_id", "setup_contexts", ["signal_id"])
    op.create_index(
        "ix_setup_contexts_analysis_run_id",
        "setup_contexts",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_setup_contexts_directional_bias",
        "setup_contexts",
        ["directional_bias"],
    )
    op.create_index(
        "ix_setup_contexts_quality_label",
        "setup_contexts",
        ["setup_quality_label"],
    )


def downgrade() -> None:
    op.drop_index("ix_setup_contexts_quality_label", table_name="setup_contexts")
    op.drop_index("ix_setup_contexts_directional_bias", table_name="setup_contexts")
    op.drop_index("ix_setup_contexts_analysis_run_id", table_name="setup_contexts")
    op.drop_index("ix_setup_contexts_signal_id", table_name="setup_contexts")
    op.drop_index("ix_setup_contexts_workspace_symbol_timeframe", table_name="setup_contexts")
    op.drop_table("setup_contexts")
