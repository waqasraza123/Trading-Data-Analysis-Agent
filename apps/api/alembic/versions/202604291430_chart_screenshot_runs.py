"""add chart screenshot prediction runs

Revision ID: 202604291430
Revises: 202604291330
Create Date: 2026-04-29 19:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291430"
down_revision: str | tuple[str, str] | None = "202604291330"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_data_sources_source_type_allowed"),
        "data_sources",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_data_sources_source_type_allowed"),
        "data_sources",
        "source_type in ('csv_upload', 'json_import', 'api_polling', "
        "'websocket_live', 'manual_seed', 'chart_screenshot')",
    )
    op.create_table(
        "chart_screenshot_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("parser_name", sa.String(length=80), nullable=False),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column("parser_source_path", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "extraction_confidence",
            sa.Numeric(precision=5, scale=4),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("raw_candle_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("stored_candle_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("conflict_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("analysis_hypothesis", sa.String(length=16), nullable=False),
        sa.Column(
            "analysis_hypothesis_confidence",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
        ),
        sa.Column("extracted_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extracted_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "extraction_warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "parser_metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("last_error_message", sa.String(length=500), nullable=True),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('received', 'parsing', 'ingested', 'analysis_triggered', "
            "'analysis_failed', 'failed', 'completed')",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_status_allowed"),
        ),
        sa.CheckConstraint(
            "analysis_hypothesis in ('bullish', 'bearish', 'neutral', 'unclear', 'unknown')",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_analysis_hypothesis_allowed"),
        ),
        sa.CheckConstraint(
            "extraction_confidence >= 0 and extraction_confidence <= 1",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_extraction_confidence_range"),
        ),
        sa.CheckConstraint(
            "analysis_hypothesis_confidence is null or "
            "(analysis_hypothesis_confidence >= 0 and analysis_hypothesis_confidence <= 1)",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_hypothesis_confidence_range"),
        ),
        sa.CheckConstraint(
            "raw_candle_count >= 0",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_raw_count_non_negative"),
        ),
        sa.CheckConstraint(
            "stored_candle_count >= 0",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_stored_count_non_negative"),
        ),
        sa.CheckConstraint(
            "duplicate_count >= 0",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_duplicate_count_non_negative"),
        ),
        sa.CheckConstraint(
            "conflict_count >= 0",
            name=op.f("ck_chart_screenshot_runs_chart_screenshot_runs_conflict_count_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_chart_screenshot_runs_analysis_run_id_analysis_runs"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_chart_screenshot_runs_source_id_data_sources"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_chart_screenshot_runs_symbol_id_symbols"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_chart_screenshot_runs_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_chart_screenshot_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chart_screenshot_runs")),
    )
    op.create_index(
        "ix_chart_screenshot_runs_workspace_id",
        "chart_screenshot_runs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_chart_screenshot_runs_workspace_source",
        "chart_screenshot_runs",
        ["workspace_id", "source_id"],
    )
    op.create_index(
        "ix_chart_screenshot_runs_symbol_timeframe",
        "chart_screenshot_runs",
        ["symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_chart_screenshot_runs_analysis_run_id",
        "chart_screenshot_runs",
        ["analysis_run_id"],
    )
    op.add_column(
        "candles",
        sa.Column("chart_screenshot_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_candles_chart_screenshot_run_id_chart_screenshot_runs"),
        "candles",
        "chart_screenshot_runs",
        ["chart_screenshot_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_candles_chart_screenshot_run_id",
        "candles",
        ["chart_screenshot_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_candles_chart_screenshot_run_id", table_name="candles")
    op.drop_constraint(
        op.f("fk_candles_chart_screenshot_run_id_chart_screenshot_runs"),
        "candles",
        type_="foreignkey",
    )
    op.drop_column("candles", "chart_screenshot_run_id")
    op.drop_index(
        "ix_chart_screenshot_runs_analysis_run_id",
        table_name="chart_screenshot_runs",
    )
    op.drop_index(
        "ix_chart_screenshot_runs_symbol_timeframe",
        table_name="chart_screenshot_runs",
    )
    op.drop_index(
        "ix_chart_screenshot_runs_workspace_source",
        table_name="chart_screenshot_runs",
    )
    op.drop_index("ix_chart_screenshot_runs_workspace_id", table_name="chart_screenshot_runs")
    op.drop_table("chart_screenshot_runs")
    op.execute(
        "update data_sources set source_type = 'manual_seed' where source_type = 'chart_screenshot'"
    )
    op.drop_constraint(
        op.f("ck_data_sources_source_type_allowed"),
        "data_sources",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_data_sources_source_type_allowed"),
        "data_sources",
        "source_type in ('csv_upload', 'json_import', 'api_polling', "
        "'websocket_live', 'manual_seed')",
    )
