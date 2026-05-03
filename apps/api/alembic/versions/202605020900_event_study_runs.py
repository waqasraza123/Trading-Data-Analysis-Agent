"""add event study runs and results

Revision ID: 202605020950_event_study_runs
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020950_event_study_runs"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_study_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("news_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("event_study_version", sa.String(length=32), nullable=False),
        sa.Column("pre_event_minutes", sa.Integer(), nullable=False),
        sa.Column("post_event_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "symbol_filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "analyzed_symbol_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("result_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "summary",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name=op.f("ck_event_study_runs_event_study_runs_status_allowed"),
        ),
        sa.CheckConstraint(
            "pre_event_minutes >= 0",
            name=op.f("ck_event_study_runs_event_study_runs_pre_minutes_non_negative"),
        ),
        sa.CheckConstraint(
            "post_event_minutes > 0",
            name=op.f("ck_event_study_runs_event_study_runs_post_minutes_positive"),
        ),
        sa.CheckConstraint(
            "analyzed_symbol_count >= 0",
            name=op.f("ck_event_study_runs_event_study_runs_analyzed_symbol_count_non_negative"),
        ),
        sa.CheckConstraint(
            "result_count >= 0",
            name=op.f("ck_event_study_runs_event_study_runs_result_count_non_negative"),
        ),
        sa.ForeignKeyConstraint(["news_event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_study_runs_workspace_news_event",
        "event_study_runs",
        ["workspace_id", "news_event_id"],
        unique=False,
    )
    op.create_table(
        "event_study_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_study_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("news_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pre_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pre_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("post_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("post_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pre_candle_count", sa.Integer(), nullable=False),
        sa.Column("post_candle_count", sa.Integer(), nullable=False),
        sa.Column("pre_move", sa.Numeric(24, 10), nullable=False),
        sa.Column("post_move", sa.Numeric(24, 10), nullable=False),
        sa.Column("post_move_pips", sa.Numeric(24, 10), nullable=True),
        sa.Column("post_move_ticks", sa.Numeric(24, 10), nullable=True),
        sa.Column(
            "pre_volatility_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "post_volatility_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("volatility_reaction", sa.String(length=32), nullable=False),
        sa.Column("direction_label", sa.String(length=32), nullable=False),
        sa.Column("reaction_label", sa.String(length=32), nullable=False),
        sa.Column("data_quality_label", sa.String(length=32), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "volatility_reaction in ('none', 'normal', 'elevated', 'spike', 'insufficient_data')",
            name=op.f("ck_event_study_results_event_study_results_volatility_reaction_allowed"),
        ),
        sa.CheckConstraint(
            "direction_label in ('bullish', 'bearish', 'neutral', 'mixed', 'insufficient_data')",
            name=op.f("ck_event_study_results_event_study_results_direction_label_allowed"),
        ),
        sa.CheckConstraint(
            "reaction_label in ('strong_reaction', 'moderate_reaction', 'weak_reaction', "
            "'no_clear_reaction', 'insufficient_data')",
            name=op.f("ck_event_study_results_event_study_results_reaction_label_allowed"),
        ),
        sa.CheckConstraint(
            "data_quality_label in ('complete', 'partial', 'insufficient_data')",
            name=op.f("ck_event_study_results_event_study_results_data_quality_label_allowed"),
        ),
        sa.CheckConstraint(
            "pre_candle_count >= 0",
            name=op.f("ck_event_study_results_event_study_results_pre_count_non_negative"),
        ),
        sa.CheckConstraint(
            "post_candle_count >= 0",
            name=op.f("ck_event_study_results_event_study_results_post_count_non_negative"),
        ),
        sa.ForeignKeyConstraint(["event_study_run_id"], ["event_study_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["news_event_id"], ["news_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["data_sources.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_event_study_results_news_symbol_timeframe",
        "event_study_results",
        ["news_event_id", "symbol_id", "timeframe"],
        unique=False,
    )
    op.create_index(
        "ix_event_study_results_reaction_label",
        "event_study_results",
        ["reaction_label"],
        unique=False,
    )
    op.create_index(
        "ix_event_study_results_run_id",
        "event_study_results",
        ["event_study_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_study_results_run_id", table_name="event_study_results")
    op.drop_index("ix_event_study_results_reaction_label", table_name="event_study_results")
    op.drop_index("ix_event_study_results_news_symbol_timeframe", table_name="event_study_results")
    op.drop_table("event_study_results")
    op.drop_index("ix_event_study_runs_workspace_news_event", table_name="event_study_runs")
    op.drop_table("event_study_runs")
