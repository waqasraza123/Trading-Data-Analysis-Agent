"""add dashboard read models

Revision ID: 202605050900_dashboard_read_models
Revises: 202605032000_daily_product_workflow_merge
Create Date: 2026-05-05 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605050900_dashboard_read_models"
down_revision: str | Sequence[str] | None = "202605032000_daily_product_workflow_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboard_symbol_read_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("read_model_version", sa.String(length=32), nullable=False),
        sa.Column("latest_final_candle_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("freshness_label", sa.String(length=32), nullable=True),
        sa.Column("data_quality_label", sa.String(length=32), nullable=True),
        sa.Column("latest_signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_bias", sa.String(length=32), nullable=True),
        sa.Column("latest_pattern_type", sa.String(length=64), nullable=True),
        sa.Column("latest_confidence_label", sa.String(length=32), nullable=True),
        sa.Column("latest_priority_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("latest_priority_label", sa.String(length=32), nullable=True),
        sa.Column("setup_quality_label", sa.String(length=32), nullable=True),
        sa.Column("market_regime_label", sa.String(length=64), nullable=True),
        sa.Column("market_session_label", sa.String(length=64), nullable=True),
        sa.Column("pending_action_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("warning_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "pending_action_count >= 0 and warning_count >= 0",
            name="dashboard_symbol_read_models_counts_non_negative",
        ),
        sa.ForeignKeyConstraint(["latest_signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_dashboard_symbol_read_models_identity",
        "dashboard_symbol_read_models",
        ["workspace_id", "symbol_id", "source_id", "timeframe", "read_model_version"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )
    op.create_index(
        "ix_dashboard_symbol_read_models_workspace_timeframe",
        "dashboard_symbol_read_models",
        ["workspace_id", "timeframe"],
    )

    op.create_table(
        "signal_card_read_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("read_model_version", sa.String(length=32), nullable=False),
        sa.Column("classification_status", sa.String(length=32), nullable=False),
        sa.Column("bias", sa.String(length=32), nullable=False),
        sa.Column("pattern_type", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("confidence_label", sa.String(length=32), nullable=True),
        sa.Column("priority_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("priority_label", sa.String(length=32), nullable=True),
        sa.Column("review_bucket", sa.String(length=48), nullable=True),
        sa.Column("setup_quality_label", sa.String(length=32), nullable=True),
        sa.Column("freshness_label", sa.String(length=32), nullable=True),
        sa.Column("data_quality_label", sa.String(length=32), nullable=True),
        sa.Column("readiness_label", sa.String(length=32), nullable=True),
        sa.Column(
            "outcome_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "evidence_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "risk_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "action_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warning_summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("searchable_text", sa.String(length=4000), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "confidence_score is null or (confidence_score >= 0 and confidence_score <= 1)",
            name="signal_card_read_models_confidence_score_range",
        ),
        sa.CheckConstraint(
            "priority_score is null or (priority_score >= 0 and priority_score <= 1)",
            name="signal_card_read_models_priority_score_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_signal_card_read_models_signal_version",
        "signal_card_read_models",
        ["signal_id", "read_model_version"],
        unique=True,
    )
    op.create_index(
        "ix_signal_card_read_models_workspace_symbol_timeframe",
        "signal_card_read_models",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_signal_card_read_models_workspace_review_bucket",
        "signal_card_read_models",
        ["workspace_id", "review_bucket"],
    )
    op.create_index(
        "ix_signal_card_read_models_workspace_priority_label",
        "signal_card_read_models",
        ["workspace_id", "priority_label"],
    )

    op.create_table(
        "command_center_read_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_model_version", sa.String(length=32), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.Column("warning_count", sa.Integer(), server_default="0", nullable=False),
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
            "warning_count >= 0",
            name="command_center_read_models_warning_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_command_center_read_models_workspace_generated",
        "command_center_read_models",
        ["workspace_id", "generated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_command_center_read_models_workspace_generated",
        table_name="command_center_read_models",
    )
    op.drop_table("command_center_read_models")
    op.drop_index(
        "ix_signal_card_read_models_workspace_priority_label",
        table_name="signal_card_read_models",
    )
    op.drop_index(
        "ix_signal_card_read_models_workspace_review_bucket",
        table_name="signal_card_read_models",
    )
    op.drop_index(
        "ix_signal_card_read_models_workspace_symbol_timeframe",
        table_name="signal_card_read_models",
    )
    op.drop_index(
        "uq_signal_card_read_models_signal_version",
        table_name="signal_card_read_models",
    )
    op.drop_table("signal_card_read_models")
    op.drop_index(
        "ix_dashboard_symbol_read_models_workspace_timeframe",
        table_name="dashboard_symbol_read_models",
    )
    op.drop_index(
        "uq_dashboard_symbol_read_models_identity",
        table_name="dashboard_symbol_read_models",
    )
    op.drop_table("dashboard_symbol_read_models")
