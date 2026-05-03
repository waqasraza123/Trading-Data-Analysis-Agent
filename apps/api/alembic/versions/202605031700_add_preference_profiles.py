"""add personal strategy preference profiles

Revision ID: 202605031700_preference_profiles
Revises: 202605031600_dashboard_digest_notifications_journal
Create Date: 2026-05-03 17:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031700_preference_profiles"
down_revision: str | Sequence[str] | None = "202605031600_dashboard_digest_notifications_journal"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "personal_strategy_preference_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "market_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "symbol_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "excluded_symbol_ids_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "timeframes_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "session_labels_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "pattern_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "excluded_pattern_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "strategy_profile_keys_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("minimum_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("minimum_setup_quality", sa.Numeric(5, 4), nullable=True),
        sa.Column("max_stale_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "require_fresh_data",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "require_timeframe_agreement",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "require_acceptable_data_quality",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_news_context",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "include_outcomes",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "notification_preferences_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
            "status in ('active', 'paused', 'archived')",
            name="personal_strategy_preference_profiles_status_allowed",
        ),
        sa.CheckConstraint(
            "minimum_confidence is null or "
            "(minimum_confidence >= 0 and minimum_confidence <= 1)",
            name="personal_strategy_preference_profiles_minimum_confidence_range",
        ),
        sa.CheckConstraint(
            "minimum_setup_quality is null or "
            "(minimum_setup_quality >= 0 and minimum_setup_quality <= 1)",
            name="personal_strategy_preference_profiles_minimum_setup_quality_range",
        ),
        sa.CheckConstraint(
            "max_stale_seconds is null or max_stale_seconds > 0",
            name="personal_strategy_preference_profiles_max_stale_positive",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_personal_strategy_preference_profiles_workspace_status",
        "personal_strategy_preference_profiles",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_personal_strategy_preference_profiles_workspace_user",
        "personal_strategy_preference_profiles",
        ["workspace_id", "user_id"],
    )
    op.create_index(
        "ix_personal_strategy_preference_profiles_workspace_default",
        "personal_strategy_preference_profiles",
        ["workspace_id", "is_default"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_personal_strategy_preference_profiles_workspace_default",
        table_name="personal_strategy_preference_profiles",
    )
    op.drop_index(
        "ix_personal_strategy_preference_profiles_workspace_user",
        table_name="personal_strategy_preference_profiles",
    )
    op.drop_index(
        "ix_personal_strategy_preference_profiles_workspace_status",
        table_name="personal_strategy_preference_profiles",
    )
    op.drop_table("personal_strategy_preference_profiles")
