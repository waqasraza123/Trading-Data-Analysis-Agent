"""add market watchlists and scheduled scans

Revision ID: 202604302100
Revises: 202604301900
Create Date: 2026-04-30 21:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604302100"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_watchlists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
            "status in ('active', 'paused', 'archived')",
            name=op.f("ck_market_watchlists_market_watchlists_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_market_watchlists_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_watchlists")),
    )
    op.create_index(
        "ix_market_watchlists_workspace_status",
        "market_watchlists",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_market_watchlists_workspace_name",
        "market_watchlists",
        ["workspace_id", "name"],
    )
    op.create_table(
        "market_watchlist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column(
            "include_partial_live_candle",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_market_watchlist_items_source_id_data_sources"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_market_watchlist_items_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["watchlist_id"],
            ["market_watchlists.id"],
            name=op.f("fk_market_watchlist_items_watchlist_id_market_watchlists"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_market_watchlist_items_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_market_watchlist_items")),
        sa.UniqueConstraint(
            "watchlist_id",
            "symbol_id",
            "source_id",
            "timeframe",
            name="uq_market_watchlist_items_watchlist_symbol_source_timeframe",
        ),
    )
    op.create_index(
        "ix_market_watchlist_items_workspace_watchlist",
        "market_watchlist_items",
        ["workspace_id", "watchlist_id"],
    )
    op.create_index(
        "ix_market_watchlist_items_symbol_timeframe",
        "market_watchlist_items",
        ["symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_market_watchlist_items_is_active",
        "market_watchlist_items",
        ["is_active"],
    )
    op.create_table(
        "scheduled_scan_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("scan_mode", sa.String(length=32), nullable=False),
        sa.Column("lookback_minutes", sa.Integer(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "include_partial_live_candle",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_news_correlation",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_ai_explanation",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_reasoning",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_action_plan",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
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
            "scan_mode in ('watchlist', 'single_symbol')",
            name=op.f("ck_scheduled_scan_configs_scheduled_scan_configs_scan_mode_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name=op.f("ck_scheduled_scan_configs_scheduled_scan_configs_status_allowed"),
        ),
        sa.CheckConstraint(
            "lookback_minutes > 0",
            name=op.f("ck_scheduled_scan_configs_scheduled_scan_configs_lookback_positive"),
        ),
        sa.CheckConstraint(
            "interval_seconds > 0",
            name=op.f("ck_scheduled_scan_configs_scheduled_scan_configs_interval_positive"),
        ),
        sa.CheckConstraint(
            "((scan_mode = 'watchlist' and watchlist_id is not null) or "
            "(scan_mode = 'single_symbol' and symbol_id is not null and timeframe is not null))",
            name=op.f("ck_scheduled_scan_configs_scheduled_scan_configs_mode_fields_required"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_scheduled_scan_configs_source_id_data_sources"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_scheduled_scan_configs_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["watchlist_id"],
            ["market_watchlists.id"],
            name=op.f("fk_scheduled_scan_configs_watchlist_id_market_watchlists"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_scheduled_scan_configs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_scan_configs")),
    )
    op.create_index(
        "ix_scheduled_scan_configs_workspace_status_next_run",
        "scheduled_scan_configs",
        ["workspace_id", "status", "next_run_at"],
    )
    op.create_index(
        "ix_scheduled_scan_configs_watchlist_id",
        "scheduled_scan_configs",
        ["watchlist_id"],
    )
    op.create_index(
        "ix_scheduled_scan_configs_symbol_timeframe",
        "scheduled_scan_configs",
        ["symbol_id", "timeframe"],
    )
    op.create_table(
        "scheduled_scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("scan_mode", sa.String(length=32), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scanned_item_count", sa.Integer(), nullable=False),
        sa.Column("analysis_run_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column(
            "analysis_run_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "signal_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("reasoning_run_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action_plan_ids_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "result_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
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
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'skipped')",
            name=op.f("ck_scheduled_scan_runs_scheduled_scan_runs_status_allowed"),
        ),
        sa.CheckConstraint(
            "scan_mode in ('watchlist', 'single_symbol')",
            name=op.f("ck_scheduled_scan_runs_scheduled_scan_runs_scan_mode_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["scan_config_id"],
            ["scheduled_scan_configs.id"],
            name=op.f("fk_scheduled_scan_runs_scan_config_id_scheduled_scan_configs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_scheduled_scan_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_scan_runs")),
    )
    op.create_index(
        "ix_scheduled_scan_runs_workspace_created",
        "scheduled_scan_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_scheduled_scan_runs_config_created",
        "scheduled_scan_runs",
        ["scan_config_id", "created_at"],
    )
    op.create_index("ix_scheduled_scan_runs_status", "scheduled_scan_runs", ["status"])
    op.create_table(
        "scheduled_scan_run_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("watchlist_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reasoning_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("skipped_reason", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
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
            "status in ('pending', 'completed', 'skipped', 'failed')",
            name=op.f("ck_scheduled_scan_run_items_scheduled_scan_run_items_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["action_plan_id"],
            ["reasoning_action_plans.id"],
            name=op.f("fk_scheduled_scan_run_items_action_plan_id_reasoning_action_plans"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_scheduled_scan_run_items_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reasoning_run_id"],
            ["llm_reasoning_runs.id"],
            name=op.f("fk_scheduled_scan_run_items_reasoning_run_id_llm_reasoning_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["scan_config_id"],
            ["scheduled_scan_configs.id"],
            name=op.f("fk_scheduled_scan_run_items_scan_config_id_scheduled_scan_configs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scan_run_id"],
            ["scheduled_scan_runs.id"],
            name=op.f("fk_scheduled_scan_run_items_scan_run_id_scheduled_scan_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_scheduled_scan_run_items_signal_id_signals"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_scheduled_scan_run_items_source_id_data_sources"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_scheduled_scan_run_items_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["watchlist_item_id"],
            ["market_watchlist_items.id"],
            name=op.f("fk_scheduled_scan_run_items_watchlist_item_id_market_watchlist_items"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_scheduled_scan_run_items_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_scheduled_scan_run_items")),
    )
    op.create_index(
        "ix_scheduled_scan_run_items_scan_run_id",
        "scheduled_scan_run_items",
        ["scan_run_id"],
    )
    op.create_index(
        "ix_scheduled_scan_run_items_symbol_timeframe",
        "scheduled_scan_run_items",
        ["symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_scheduled_scan_run_items_status",
        "scheduled_scan_run_items",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_scan_run_items_status", table_name="scheduled_scan_run_items")
    op.drop_index(
        "ix_scheduled_scan_run_items_symbol_timeframe",
        table_name="scheduled_scan_run_items",
    )
    op.drop_index(
        "ix_scheduled_scan_run_items_scan_run_id",
        table_name="scheduled_scan_run_items",
    )
    op.drop_table("scheduled_scan_run_items")
    op.drop_index("ix_scheduled_scan_runs_status", table_name="scheduled_scan_runs")
    op.drop_index("ix_scheduled_scan_runs_config_created", table_name="scheduled_scan_runs")
    op.drop_index("ix_scheduled_scan_runs_workspace_created", table_name="scheduled_scan_runs")
    op.drop_table("scheduled_scan_runs")
    op.drop_index(
        "ix_scheduled_scan_configs_symbol_timeframe",
        table_name="scheduled_scan_configs",
    )
    op.drop_index("ix_scheduled_scan_configs_watchlist_id", table_name="scheduled_scan_configs")
    op.drop_index(
        "ix_scheduled_scan_configs_workspace_status_next_run",
        table_name="scheduled_scan_configs",
    )
    op.drop_table("scheduled_scan_configs")
    op.drop_index("ix_market_watchlist_items_is_active", table_name="market_watchlist_items")
    op.drop_index(
        "ix_market_watchlist_items_symbol_timeframe",
        table_name="market_watchlist_items",
    )
    op.drop_index(
        "ix_market_watchlist_items_workspace_watchlist",
        table_name="market_watchlist_items",
    )
    op.drop_table("market_watchlist_items")
    op.drop_index("ix_market_watchlists_workspace_name", table_name="market_watchlists")
    op.drop_index("ix_market_watchlists_workspace_status", table_name="market_watchlists")
    op.drop_table("market_watchlists")
