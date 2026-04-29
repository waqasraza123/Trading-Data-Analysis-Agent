"""create core database schema

Revision ID: 202604290620
Revises:
Create Date: 2026-04-29 06:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604290620"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    op.create_table(
        "symbols",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("market_type", sa.String(length=32), nullable=False),
        sa.Column("base_asset", sa.String(length=32), nullable=True),
        sa.Column("quote_asset", sa.String(length=32), nullable=True),
        sa.Column("pip_size", sa.Numeric(24, 10), nullable=True),
        sa.Column("tick_size", sa.Numeric(24, 10), nullable=True),
        sa.Column("price_precision", sa.Integer(), server_default="10", nullable=False),
        sa.Column("quantity_precision", sa.Integer(), server_default="10", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
            "market_type in ('forex', 'crypto', 'stock', 'index', 'commodity')",
            name=op.f("ck_symbols_market_type_allowed"),
        ),
        sa.CheckConstraint(
            "pip_size is null or pip_size > 0",
            name=op.f("ck_symbols_pip_size_positive"),
        ),
        sa.CheckConstraint(
            "tick_size is null or tick_size > 0",
            name=op.f("ck_symbols_tick_size_positive"),
        ),
        sa.CheckConstraint(
            "price_precision >= 0",
            name=op.f("ck_symbols_price_precision_non_negative"),
        ),
        sa.CheckConstraint(
            "quantity_precision >= 0",
            name=op.f("ck_symbols_quantity_precision_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_symbols")),
    )
    op.create_index("ix_symbols_symbol", "symbols", ["symbol"], unique=True)
    op.create_index("ix_symbols_market_type", "symbols", ["market_type"], unique=False)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "role in ('admin', 'user', 'analyst')",
            name=op.f("ck_users_role_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_users_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("workspace_id", "email", name="uq_users_workspace_email"),
    )
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"], unique=False)
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "source_type in ('csv_upload', 'json_import', 'api_polling', "
            "'websocket_live', 'manual_seed')",
            name=op.f("ck_data_sources_source_type_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('active', 'inactive', 'failed')",
            name=op.f("ck_data_sources_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_sources_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_sources")),
    )
    op.create_index("ix_data_sources_workspace_id", "data_sources", ["workspace_id"], unique=False)
    op.create_index("ix_data_sources_source_type", "data_sources", ["source_type"], unique=False)
    op.create_table(
        "engine_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_name", sa.String(length=80), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_engine_versions")),
        sa.UniqueConstraint("engine_name", "version", name="uq_engine_versions_engine_version"),
    )
    op.create_index(
        "ix_engine_versions_engine_name", "engine_versions", ["engine_name"], unique=False
    )
    op.create_table(
        "import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("rows_received", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_valid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_invalid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("duplicates_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("missing_candles_detected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("data_quality_score", sa.Numeric(6, 5), nullable=True),
        sa.Column("error_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status in ('pending', 'processing', 'completed', "
            "'completed_with_warnings', 'failed', 'cancelled')",
            name=op.f("ck_import_batches_status_allowed"),
        ),
        sa.CheckConstraint(
            "rows_received >= 0",
            name=op.f("ck_import_batches_rows_received_non_negative"),
        ),
        sa.CheckConstraint(
            "rows_valid >= 0",
            name=op.f("ck_import_batches_rows_valid_non_negative"),
        ),
        sa.CheckConstraint(
            "rows_invalid >= 0",
            name=op.f("ck_import_batches_rows_invalid_non_negative"),
        ),
        sa.CheckConstraint(
            "duplicates_skipped >= 0",
            name=op.f("ck_import_batches_duplicates_skipped_non_negative"),
        ),
        sa.CheckConstraint(
            "missing_candles_detected >= 0",
            name=op.f("ck_import_batches_missing_candles_detected_non_negative"),
        ),
        sa.CheckConstraint(
            "data_quality_score is null or (data_quality_score >= 0 and data_quality_score <= 1)",
            name=op.f("ck_import_batches_data_quality_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_import_batches_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_import_batches_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_import_batches_source_id_data_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_import_batches_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_batches")),
    )
    op.create_index(
        "ix_import_batches_workspace_id", "import_batches", ["workspace_id"], unique=False
    )
    op.create_index(
        "ix_import_batches_symbol_timeframe",
        "import_batches",
        ["symbol_id", "timeframe"],
        unique=False,
    )
    op.create_index("ix_import_batches_status", "import_batches", ["status"], unique=False)
    op.create_table(
        "live_feed_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_final_candle_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column(
            "config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status in ('active', 'paused', 'failed', 'stopped', 'stale')",
            name=op.f("ck_live_feed_subscriptions_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_live_feed_subscriptions_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_live_feed_subscriptions_source_id_data_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_live_feed_subscriptions_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_feed_subscriptions")),
    )
    op.create_index(
        "ix_live_feed_subscriptions_workspace_id",
        "live_feed_subscriptions",
        ["workspace_id"],
        unique=False,
    )
    op.create_index(
        "ix_live_feed_subscriptions_source_id",
        "live_feed_subscriptions",
        ["source_id"],
        unique=False,
    )
    op.create_index(
        "ix_live_feed_subscriptions_symbol_timeframe",
        "live_feed_subscriptions",
        ["symbol_id", "timeframe"],
        unique=False,
    )
    op.create_index(
        "ix_live_feed_subscriptions_status", "live_feed_subscriptions", ["status"], unique=False
    )
    op.create_table(
        "live_feed_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "event_type in ('candle_partial', 'candle_final', 'heartbeat', "
            "'reconnect', 'error', 'snapshot')",
            name=op.f("ck_live_feed_events_event_type_allowed"),
        ),
        sa.CheckConstraint(
            "processing_status in ('received', 'processed', 'ignored', 'failed')",
            name=op.f("ck_live_feed_events_processing_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_live_feed_events_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_live_feed_events_source_id_data_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["live_feed_subscriptions.id"],
            name=op.f("fk_live_feed_events_subscription_id_live_feed_subscriptions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_live_feed_events")),
    )
    op.create_index(
        "ix_live_feed_events_workspace_id", "live_feed_events", ["workspace_id"], unique=False
    )
    op.create_index(
        "ix_live_feed_events_source_id", "live_feed_events", ["source_id"], unique=False
    )
    op.create_index(
        "ix_live_feed_events_subscription_id", "live_feed_events", ["subscription_id"], unique=False
    )
    op.create_index(
        "ix_live_feed_events_received_at", "live_feed_events", ["received_at"], unique=False
    )
    op.create_index(
        "ix_live_feed_events_processing_status",
        "live_feed_events",
        ["processing_status"],
        unique=False,
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warmup_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("baseline_start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_mode", sa.String(length=32), nullable=False),
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
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column("rule_set_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "analysis_mode in ('historical', 'live_window', 'scheduled_scan', 'replay')",
            name=op.f("ck_analysis_runs_analysis_mode_allowed"),
        ),
        sa.CheckConstraint(
            "status in ('queued', 'running', 'completed', 'failed', "
            "'insufficient_data', 'cancelled')",
            name=op.f("ck_analysis_runs_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_analysis_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_analysis_runs_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_analysis_runs_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_analysis_runs_source_id_data_sources"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_runs")),
    )
    op.create_index(
        "ix_analysis_runs_workspace_id", "analysis_runs", ["workspace_id"], unique=False
    )
    op.create_index(
        "ix_analysis_runs_symbol_timeframe",
        "analysis_runs",
        ["symbol_id", "timeframe"],
        unique=False,
    )
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"], unique=False)
    op.create_index(
        "ix_analysis_runs_window", "analysis_runs", ["start_time", "end_time"], unique=False
    )
    op.create_table(
        "import_errors",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.String(length=500), nullable=False),
        sa.Column("raw_row_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name=op.f("fk_import_errors_import_batch_id_import_batches"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_import_errors")),
    )
    op.create_index(
        "ix_import_errors_import_batch_id", "import_errors", ["import_batch_id"], unique=False
    )
    op.create_index("ix_import_errors_error_code", "import_errors", ["error_code"], unique=False)
    op.create_table(
        "analysis_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_analysis_audit_logs_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_analysis_audit_logs")),
    )
    op.create_index(
        "ix_analysis_audit_logs_analysis_run_id",
        "analysis_audit_logs",
        ["analysis_run_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_audit_logs_event_type", "analysis_audit_logs", ["event_type"], unique=False
    )
    op.create_table(
        "candles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("live_feed_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(24, 10), nullable=False),
        sa.Column("high", sa.Numeric(24, 10), nullable=False),
        sa.Column("low", sa.Numeric(24, 10), nullable=False),
        sa.Column("close", sa.Numeric(24, 10), nullable=False),
        sa.Column("volume", sa.Numeric(30, 10), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("quality_score", sa.Numeric(6, 5), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("open > 0", name=op.f("ck_candles_open_positive")),
        sa.CheckConstraint("high > 0", name=op.f("ck_candles_high_positive")),
        sa.CheckConstraint("low > 0", name=op.f("ck_candles_low_positive")),
        sa.CheckConstraint("close > 0", name=op.f("ck_candles_close_positive")),
        sa.CheckConstraint("high >= open", name=op.f("ck_candles_high_gte_open")),
        sa.CheckConstraint("high >= close", name=op.f("ck_candles_high_gte_close")),
        sa.CheckConstraint("high >= low", name=op.f("ck_candles_high_gte_low")),
        sa.CheckConstraint("low <= open", name=op.f("ck_candles_low_lte_open")),
        sa.CheckConstraint("low <= close", name=op.f("ck_candles_low_lte_close")),
        sa.CheckConstraint(
            "volume is null or volume >= 0", name=op.f("ck_candles_volume_non_negative")
        ),
        sa.CheckConstraint(
            "quality_score is null or (quality_score >= 0 and quality_score <= 1)",
            name=op.f("ck_candles_quality_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_candles_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_candles_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_candles_source_id_data_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            name=op.f("fk_candles_import_batch_id_import_batches"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["live_feed_event_id"],
            ["live_feed_events.id"],
            name=op.f("fk_candles_live_feed_event_id_live_feed_events"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_candles")),
        sa.UniqueConstraint(
            "workspace_id",
            "symbol_id",
            "source_id",
            "timeframe",
            "timestamp",
            name="uq_candles_workspace_symbol_source_timeframe_timestamp",
        ),
    )
    op.create_index(
        "ix_candles_workspace_symbol_timeframe_timestamp",
        "candles",
        ["workspace_id", "symbol_id", "timeframe", "timestamp"],
        unique=False,
    )
    op.create_index(
        "ix_candles_workspace_symbol_timeframe_timestamp_is_final",
        "candles",
        ["workspace_id", "symbol_id", "timeframe", "timestamp", "is_final"],
        unique=False,
    )
    op.create_index(
        "ix_candles_source_timestamp", "candles", ["source_id", "timestamp"], unique=False
    )
    op.create_index("ix_candles_import_batch_id", "candles", ["import_batch_id"], unique=False)
    op.create_index(
        "ix_candles_live_feed_event_id", "candles", ["live_feed_event_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_candles_live_feed_event_id", table_name="candles")
    op.drop_index("ix_candles_import_batch_id", table_name="candles")
    op.drop_index("ix_candles_source_timestamp", table_name="candles")
    op.drop_index("ix_candles_workspace_symbol_timeframe_timestamp_is_final", table_name="candles")
    op.drop_index("ix_candles_workspace_symbol_timeframe_timestamp", table_name="candles")
    op.drop_table("candles")
    op.drop_index("ix_analysis_audit_logs_event_type", table_name="analysis_audit_logs")
    op.drop_index("ix_analysis_audit_logs_analysis_run_id", table_name="analysis_audit_logs")
    op.drop_table("analysis_audit_logs")
    op.drop_index("ix_import_errors_error_code", table_name="import_errors")
    op.drop_index("ix_import_errors_import_batch_id", table_name="import_errors")
    op.drop_table("import_errors")
    op.drop_index("ix_analysis_runs_window", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_status", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_symbol_timeframe", table_name="analysis_runs")
    op.drop_index("ix_analysis_runs_workspace_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_index("ix_live_feed_events_processing_status", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_received_at", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_subscription_id", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_source_id", table_name="live_feed_events")
    op.drop_index("ix_live_feed_events_workspace_id", table_name="live_feed_events")
    op.drop_table("live_feed_events")
    op.drop_index("ix_live_feed_subscriptions_status", table_name="live_feed_subscriptions")
    op.drop_index(
        "ix_live_feed_subscriptions_symbol_timeframe", table_name="live_feed_subscriptions"
    )
    op.drop_index("ix_live_feed_subscriptions_source_id", table_name="live_feed_subscriptions")
    op.drop_index("ix_live_feed_subscriptions_workspace_id", table_name="live_feed_subscriptions")
    op.drop_table("live_feed_subscriptions")
    op.drop_index("ix_import_batches_status", table_name="import_batches")
    op.drop_index("ix_import_batches_symbol_timeframe", table_name="import_batches")
    op.drop_index("ix_import_batches_workspace_id", table_name="import_batches")
    op.drop_table("import_batches")
    op.drop_index("ix_engine_versions_engine_name", table_name="engine_versions")
    op.drop_table("engine_versions")
    op.drop_index("ix_data_sources_source_type", table_name="data_sources")
    op.drop_index("ix_data_sources_workspace_id", table_name="data_sources")
    op.drop_table("data_sources")
    op.drop_index("ix_users_workspace_id", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_symbols_market_type", table_name="symbols")
    op.drop_index("ix_symbols_symbol", table_name="symbols")
    op.drop_table("symbols")
    op.drop_table("workspaces")
