"""integrate advanced intelligence operations

Revision ID: 202605021240_advanced_intelligence_operations
Revises: 202605021100_decision_readiness_assessments, 202605021110_strategy_profile_simulations
Create Date: 2026-05-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605021240_advanced_intelligence_operations"
down_revision: str | Sequence[str] | None = (
    "202605021100_decision_readiness_assessments",
    "202605021110_strategy_profile_simulations",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_quality_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quality_version", sa.String(length=32), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("live_subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("candle_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("finding_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quality_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("quality_label", sa.String(length=32), nullable=False),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="data_quality_runs_status_allowed",
        ),
        sa.CheckConstraint(
            "scope_type in ('candle_range', 'data_source', 'live_subscription')",
            name="data_quality_runs_scope_type_allowed",
        ),
        sa.CheckConstraint(
            "quality_label in ('strong', 'acceptable', 'degraded', 'poor', 'insufficient_data')",
            name="data_quality_runs_quality_label_allowed",
        ),
        sa.CheckConstraint(
            "quality_score >= 0 and quality_score <= 1",
            name="data_quality_runs_quality_score_range",
        ),
        sa.CheckConstraint(
            "candle_count >= 0 and finding_count >= 0", name="data_quality_runs_counts_non_negative"
        ),
        sa.ForeignKeyConstraint(
            ["live_subscription_id"], ["live_feed_subscriptions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_quality_runs_workspace_scope", "data_quality_runs", ["workspace_id", "scope_type"]
    )
    op.create_index("ix_data_quality_runs_quality_label", "data_quality_runs", ["quality_label"])
    op.create_table(
        "data_quality_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_quality_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
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
            "severity in ('info', 'low', 'medium', 'high')",
            name="data_quality_findings_severity_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["data_quality_run_id"], ["data_quality_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_data_quality_findings_run_id", "data_quality_findings", ["data_quality_run_id"]
    )
    op.create_index(
        "ix_data_quality_findings_workspace_severity",
        "data_quality_findings",
        ["workspace_id", "severity"],
    )
    op.create_index(
        "ix_data_quality_findings_finding_type", "data_quality_findings", ["finding_type"]
    )
    op.create_table(
        "intelligence_dataset_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "redaction_policy_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("requested_limit", sa.Integer(), nullable=False),
        sa.Column("item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "summary_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="intelligence_dataset_exports_status_allowed",
        ),
        sa.CheckConstraint(
            "export_format in ('jsonl')", name="intelligence_dataset_exports_format_allowed"
        ),
        sa.CheckConstraint(
            "requested_limit > 0 and item_count >= 0",
            name="intelligence_dataset_exports_counts_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_dataset_exports_workspace_status",
        "intelligence_dataset_exports",
        ["workspace_id", "status"],
    )
    op.create_table(
        "intelligence_dataset_export_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("item_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "redaction_json",
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
            "sequence_number > 0", name="intelligence_dataset_export_items_sequence"
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["export_id"], ["intelligence_dataset_exports.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_dataset_export_items_export_id",
        "intelligence_dataset_export_items",
        ["export_id"],
    )
    op.create_index(
        "ix_intelligence_dataset_export_items_signal_id",
        "intelligence_dataset_export_items",
        ["signal_id"],
    )
    op.create_table(
        "market_session_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("context_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone_name", sa.String(length=64), nullable=False),
        sa.Column("session_version", sa.String(length=32), nullable=False),
        sa.Column("session_label", sa.String(length=32), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column(
            "context_json",
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
            "session_label in ('asia', 'london', 'new_york', 'overlap', 'off_hours', 'unknown')",
            name="market_session_contexts_session_label_allowed",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 and confidence_score <= 1",
            name="market_session_contexts_confidence_range",
        ),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_session_contexts_analysis_run_id", "market_session_contexts", ["analysis_run_id"]
    )
    op.create_index(
        "ix_market_session_contexts_signal_id", "market_session_contexts", ["signal_id"]
    )
    op.create_index(
        "ix_market_session_contexts_workspace_label",
        "market_session_contexts",
        ["workspace_id", "session_label"],
    )
    op.create_table(
        "operator_playbooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "rules_json",
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
        sa.CheckConstraint("priority >= 0", name="operator_playbooks_priority_non_negative"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_operator_playbooks_key_version", "operator_playbooks", ["key", "version"], unique=True
    )
    op.create_index("ix_operator_playbooks_enabled", "operator_playbooks", ["is_enabled"])
    op.create_table(
        "operator_playbook_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("playbook_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("recommendation_type", sa.String(length=48), nullable=False),
        sa.Column("subject_type", sa.String(length=48), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "result_json",
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
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="operator_playbook_evaluations_status_allowed",
        ),
        sa.CheckConstraint(
            "recommendation_type in ('review_data_quality', 'review_profile_simulation', "
            "'review_decision_readiness', 'review_market_session', 'no_action')",
            name="operator_playbook_evaluations_recommendation_allowed",
        ),
        sa.ForeignKeyConstraint(["playbook_id"], ["operator_playbooks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_operator_playbook_evaluations_workspace_created",
        "operator_playbook_evaluations",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_operator_playbook_evaluations_playbook_id",
        "operator_playbook_evaluations",
        ["playbook_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operator_playbook_evaluations_playbook_id", table_name="operator_playbook_evaluations"
    )
    op.drop_index(
        "ix_operator_playbook_evaluations_workspace_created",
        table_name="operator_playbook_evaluations",
    )
    op.drop_table("operator_playbook_evaluations")
    op.drop_index("ix_operator_playbooks_enabled", table_name="operator_playbooks")
    op.drop_index("uq_operator_playbooks_key_version", table_name="operator_playbooks")
    op.drop_table("operator_playbooks")
    op.drop_index(
        "ix_market_session_contexts_workspace_label", table_name="market_session_contexts"
    )
    op.drop_index("ix_market_session_contexts_signal_id", table_name="market_session_contexts")
    op.drop_index(
        "ix_market_session_contexts_analysis_run_id", table_name="market_session_contexts"
    )
    op.drop_table("market_session_contexts")
    op.drop_index(
        "ix_intelligence_dataset_export_items_signal_id",
        table_name="intelligence_dataset_export_items",
    )
    op.drop_index(
        "ix_intelligence_dataset_export_items_export_id",
        table_name="intelligence_dataset_export_items",
    )
    op.drop_table("intelligence_dataset_export_items")
    op.drop_index(
        "ix_intelligence_dataset_exports_workspace_status",
        table_name="intelligence_dataset_exports",
    )
    op.drop_table("intelligence_dataset_exports")
    op.drop_index("ix_data_quality_findings_finding_type", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_workspace_severity", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_run_id", table_name="data_quality_findings")
    op.drop_table("data_quality_findings")
    op.drop_index("ix_data_quality_runs_quality_label", table_name="data_quality_runs")
    op.drop_index("ix_data_quality_runs_workspace_scope", table_name="data_quality_runs")
    op.drop_table("data_quality_runs")
