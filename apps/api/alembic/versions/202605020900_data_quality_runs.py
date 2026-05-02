"""data quality runs

Revision ID: 202605020900
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020900"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_quality_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quality_score", sa.Numeric(6, 5), nullable=False),
        sa.Column("quality_label", sa.String(length=32), nullable=False),
        sa.Column("checked_candle_count", sa.Integer(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "scope_type in ('candle_range', 'data_source', 'live_subscription', 'workspace')",
            name=op.f("ck_data_quality_runs_scope_type_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name=op.f("ck_data_quality_runs_status_allowed"),
        ),
        sa.CheckConstraint(
            "quality_label in ('strong', 'acceptable', 'degraded', 'poor', 'insufficient')",
            name=op.f("ck_data_quality_runs_quality_label_allowed"),
        ),
        sa.CheckConstraint(
            "quality_score >= 0 and quality_score <= 1",
            name=op.f("ck_data_quality_runs_quality_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_data_quality_runs_source_id_data_sources"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_data_quality_runs_symbol_id_symbols"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_quality_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_quality_runs")),
    )
    op.create_index(
        "ix_data_quality_runs_workspace_created_at",
        "data_quality_runs",
        ["workspace_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_data_quality_runs_symbol_timeframe",
        "data_quality_runs",
        ["symbol_id", "timeframe"],
        unique=False,
    )
    op.create_table(
        "data_quality_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_quality_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("live_subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("expected_value", sa.String(length=250), nullable=True),
        sa.Column("observed_value", sa.String(length=250), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "finding_type in ('missing_candles', 'duplicate_candles', "
            "'conflicting_final_candle', 'partial_after_final', "
            "'timestamp_misalignment', 'stale_live_feed', 'outlier_range', "
            "'zero_volume', 'invalid_price_gap', 'low_completeness', "
            "'source_inconsistency')",
            name=op.f("ck_data_quality_findings_finding_type_allowed"),
        ),
        sa.CheckConstraint(
            "severity in ('info', 'low', 'medium', 'high', 'critical')",
            name=op.f("ck_data_quality_findings_severity_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["data_quality_run_id"],
            ["data_quality_runs.id"],
            name=op.f("fk_data_quality_findings_data_quality_run_id_data_quality_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["live_subscription_id"],
            ["live_feed_subscriptions.id"],
            name=op.f("fk_data_quality_findings_live_subscription_id_live_feed_subscriptions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_data_quality_findings_source_id_data_sources"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_data_quality_findings_symbol_id_symbols"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_quality_findings_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_quality_findings")),
    )
    op.create_index(
        "ix_data_quality_findings_run_id",
        "data_quality_findings",
        ["data_quality_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_data_quality_findings_type_severity",
        "data_quality_findings",
        ["finding_type", "severity"],
        unique=False,
    )
    op.create_index(
        "ix_data_quality_findings_symbol_timeframe_timestamp",
        "data_quality_findings",
        ["symbol_id", "timeframe", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_data_quality_findings_symbol_timeframe_timestamp",
        table_name="data_quality_findings",
    )
    op.drop_index("ix_data_quality_findings_type_severity", table_name="data_quality_findings")
    op.drop_index("ix_data_quality_findings_run_id", table_name="data_quality_findings")
    op.drop_table("data_quality_findings")
    op.drop_index("ix_data_quality_runs_symbol_timeframe", table_name="data_quality_runs")
    op.drop_index("ix_data_quality_runs_workspace_created_at", table_name="data_quality_runs")
    op.drop_table("data_quality_runs")
