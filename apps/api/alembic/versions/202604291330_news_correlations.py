"""add deterministic news correlations

Revision ID: 202604291330
Revises: f9eb9423c4a2
Create Date: 2026-04-29 18:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202604291330"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("asset", sa.String(length=32), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("importance", sa.String(length=16), server_default="unknown", nullable=False),
        sa.Column("sentiment", sa.String(length=16), server_default="unknown", nullable=False),
        sa.Column("actual_value", sa.String(length=120), nullable=True),
        sa.Column("forecast_value", sa.String(length=120), nullable=True),
        sa.Column("previous_value", sa.String(length=120), nullable=True),
        sa.Column("impact_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column(
            "raw_payload_json",
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
            "event_type in ('economic_calendar', 'market_news', 'crypto_event', "
            "'earnings', 'central_bank', 'manual')",
            name=op.f("ck_news_events_news_event_type_allowed"),
        ),
        sa.CheckConstraint(
            "importance in ('low', 'medium', 'high', 'critical', 'unknown')",
            name=op.f("ck_news_events_news_importance_allowed"),
        ),
        sa.CheckConstraint(
            "sentiment in ('bullish', 'bearish', 'neutral', 'mixed', 'unknown')",
            name=op.f("ck_news_events_news_sentiment_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_news_events_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["symbol_id"],
            ["symbols.id"],
            name=op.f("fk_news_events_symbol_id_symbols"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_news_events")),
    )
    op.create_index("ix_news_events_workspace_time", "news_events", ["workspace_id", "event_time"])
    op.create_index("ix_news_events_currency_time", "news_events", ["currency", "event_time"])
    op.create_index("ix_news_events_asset_time", "news_events", ["asset", "event_time"])
    op.create_index("ix_news_events_symbol_time", "news_events", ["symbol_id", "event_time"])

    op.create_table(
        "signal_news_correlations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("news_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("correlation_label", sa.String(length=16), nullable=False),
        sa.Column("time_delta_minutes", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("direction_alignment", sa.String(length=16), nullable=False),
        sa.Column("volatility_reaction", sa.String(length=16), nullable=False),
        sa.Column("relevance_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("importance_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("magnitude_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
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
        sa.CheckConstraint(
            "correlation_score >= 0 and correlation_score <= 1",
            name=op.f("ck_signal_news_correlations_signal_news_correlation_score_range"),
        ),
        sa.CheckConstraint(
            "relevance_score >= 0 and relevance_score <= 1",
            name=op.f("ck_signal_news_correlations_signal_news_relevance_score_range"),
        ),
        sa.CheckConstraint(
            "importance_score >= 0 and importance_score <= 1",
            name=op.f("ck_signal_news_correlations_signal_news_importance_score_range"),
        ),
        sa.CheckConstraint(
            "magnitude_score >= 0 and magnitude_score <= 1",
            name=op.f("ck_signal_news_correlations_signal_news_magnitude_score_range"),
        ),
        sa.CheckConstraint(
            "sentiment_score >= 0 and sentiment_score <= 1",
            name=op.f("ck_signal_news_correlations_signal_news_sentiment_score_range"),
        ),
        sa.CheckConstraint(
            "correlation_label in ('none', 'weak', 'possible', 'strong')",
            name=op.f("ck_signal_news_correlations_signal_news_correlation_label_allowed"),
        ),
        sa.CheckConstraint(
            "direction_alignment in ('aligned', 'opposed', 'neutral', 'unknown')",
            name=op.f("ck_signal_news_correlations_signal_news_direction_alignment_allowed"),
        ),
        sa.CheckConstraint(
            "volatility_reaction in ('none', 'normal', 'elevated', 'spike', 'unknown')",
            name=op.f("ck_signal_news_correlations_signal_news_volatility_reaction_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_run_id"],
            ["analysis_runs.id"],
            name=op.f("fk_signal_news_correlations_analysis_run_id_analysis_runs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["news_event_id"],
            ["news_events.id"],
            name=op.f("fk_signal_news_correlations_news_event_id_news_events"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["signals.id"],
            name=op.f("fk_signal_news_correlations_signal_id_signals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_signal_news_correlations_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_signal_news_correlations")),
    )
    op.create_index(
        "ix_signal_news_correlations_signal_id",
        "signal_news_correlations",
        ["signal_id"],
    )
    op.create_index(
        "ix_signal_news_correlations_analysis_run_id",
        "signal_news_correlations",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_signal_news_correlations_news_event_id",
        "signal_news_correlations",
        ["news_event_id"],
    )
    op.create_index(
        "ix_signal_news_correlations_label",
        "signal_news_correlations",
        ["correlation_label"],
    )


def downgrade() -> None:
    op.drop_index("ix_signal_news_correlations_label", table_name="signal_news_correlations")
    op.drop_index(
        "ix_signal_news_correlations_news_event_id",
        table_name="signal_news_correlations",
    )
    op.drop_index(
        "ix_signal_news_correlations_analysis_run_id",
        table_name="signal_news_correlations",
    )
    op.drop_index("ix_signal_news_correlations_signal_id", table_name="signal_news_correlations")
    op.drop_table("signal_news_correlations")
    op.drop_index("ix_news_events_symbol_time", table_name="news_events")
    op.drop_index("ix_news_events_asset_time", table_name="news_events")
    op.drop_index("ix_news_events_currency_time", table_name="news_events")
    op.drop_index("ix_news_events_workspace_time", table_name="news_events")
    op.drop_table("news_events")
