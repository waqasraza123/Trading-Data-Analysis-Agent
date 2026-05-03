"""add intelligence catalog

Revision ID: 202605021200
Revises: f9eb9423c4a2
Create Date: 2026-05-02 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605021200"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_catalog_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("symbol_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timeframe", sa.String(length=16), nullable=True),
        sa.Column("strategy_profile_key", sa.String(length=80), nullable=True),
        sa.Column("pattern_type", sa.String(length=80), nullable=True),
        sa.Column("bias", sa.String(length=32), nullable=True),
        sa.Column("classification_status", sa.String(length=64), nullable=True),
        sa.Column("quality_label", sa.String(length=64), nullable=True),
        sa.Column("readiness_label", sa.String(length=64), nullable=True),
        sa.Column("outcome_label", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column(
            "tags_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("searchable_text", sa.Text(), nullable=False),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("artifact_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "artifact_type",
            "artifact_id",
            name="uq_intelligence_catalog_items_workspace_artifact",
        ),
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_artifact_type",
        "intelligence_catalog_items",
        ["workspace_id", "artifact_type"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_status",
        "intelligence_catalog_items",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_symbol_timeframe",
        "intelligence_catalog_items",
        ["workspace_id", "symbol_id", "timeframe"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_strategy_profile",
        "intelligence_catalog_items",
        ["workspace_id", "strategy_profile_key"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_pattern_type",
        "intelligence_catalog_items",
        ["workspace_id", "pattern_type"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_bias",
        "intelligence_catalog_items",
        ["workspace_id", "bias"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_outcome_label",
        "intelligence_catalog_items",
        ["workspace_id", "outcome_label"],
    )
    op.create_index(
        "ix_intelligence_catalog_items_workspace_indexed_at",
        "intelligence_catalog_items",
        ["workspace_id", "indexed_at"],
    )


def downgrade() -> None:
    op.drop_table("intelligence_catalog_items")
