"""add scanner presets

Revision ID: 202605031900_scanner_presets
Revises: 202605031800_merge_daily_workflow_heads
Create Date: 2026-05-03 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605031900_scanner_presets"
down_revision: str | Sequence[str] | None = "202605031800_merge_daily_workflow_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scanner_presets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("key", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("preset_version", sa.String(length=32), nullable=False),
        sa.Column(
            "market_types_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "symbol_templates_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "timeframe_templates_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "session_filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "scan_config_template_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "watchlist_template_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "preference_profile_filters_json",
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
            "category in ('session', 'market', 'volatility', 'pattern_context', "
            "'data_repair', 'review')",
            name="scanner_presets_category_allowed",
        ),
        sa.CheckConstraint(
            "status in ('active', 'archived')",
            name="scanner_presets_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scanner_presets_key_version", "scanner_presets", ["key", "preset_version"])
    op.create_index(
        "ix_scanner_presets_category_status",
        "scanner_presets",
        ["category", "status"],
    )
    op.create_index("ix_scanner_presets_workspace_key", "scanner_presets", ["workspace_id", "key"])

    op.create_table(
        "scanner_preset_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scanner_preset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("watchlist_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scan_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preference_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "applied_config_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
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
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="scanner_preset_applications_status_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scanner_preset_id"],
            ["scanner_presets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["watchlist_id"], ["market_watchlists.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["scan_config_id"],
            ["scheduled_scan_configs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["preference_profile_id"],
            ["personal_strategy_preference_profiles.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scanner_preset_applications_workspace_preset",
        "scanner_preset_applications",
        ["workspace_id", "scanner_preset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scanner_preset_applications_workspace_preset",
        table_name="scanner_preset_applications",
    )
    op.drop_table("scanner_preset_applications")
    op.drop_index("ix_scanner_presets_workspace_key", table_name="scanner_presets")
    op.drop_index("ix_scanner_presets_category_status", table_name="scanner_presets")
    op.drop_index("ix_scanner_presets_key_version", table_name="scanner_presets")
    op.drop_table("scanner_presets")
