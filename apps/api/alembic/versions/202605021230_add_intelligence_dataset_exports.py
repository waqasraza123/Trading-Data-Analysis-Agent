"""add intelligence dataset exports

Revision ID: 202605021250_intelligence_dataset_exports
Revises: 202605021240_advanced_intelligence_operations
Create Date: 2026-05-02 12:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605021250_intelligence_dataset_exports"
down_revision: str | tuple[str, str] | None = "202605021240_advanced_intelligence_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_dataset_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dataset_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "filters_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("record_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "redaction_policy_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "manifest_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("storage_mode", sa.String(length=32), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "dataset_type in ('signal_supervision', 'outcome_evaluation', "
            "'reasoning_grounding', 'quality_review', 'screenshot_review', "
            "'mixed_intelligence')",
            name="intelligence_dataset_exports_dataset_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="intelligence_dataset_exports_status_allowed",
        ),
        sa.CheckConstraint(
            "storage_mode in ('inline_json', 'manifest_only')",
            name="intelligence_dataset_exports_storage_mode_allowed",
        ),
        sa.CheckConstraint(
            "record_count >= 0",
            name="intelligence_dataset_exports_record_count_non_negative",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_dataset_exports_workspace_created",
        "intelligence_dataset_exports",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_intelligence_dataset_exports_dataset_type_status",
        "intelligence_dataset_exports",
        ["dataset_type", "status"],
    )
    op.create_table(
        "intelligence_dataset_export_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("export_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_key", sa.String(length=240), nullable=False),
        sa.Column(
            "record_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "redaction_warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "source_type in ('signal', 'analysis_run', 'outcome', 'reasoning_run', "
            "'quality_run', 'screenshot_decision')",
            name="intelligence_dataset_export_items_source_type_allowed",
        ),
        sa.ForeignKeyConstraint(["export_id"], ["intelligence_dataset_exports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_intelligence_dataset_export_items_export_id",
        "intelligence_dataset_export_items",
        ["export_id"],
    )
    op.create_index(
        "ix_intelligence_dataset_export_items_source_type_source_id",
        "intelligence_dataset_export_items",
        ["source_type", "source_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_intelligence_dataset_export_items_source_type_source_id",
        table_name="intelligence_dataset_export_items",
    )
    op.drop_index(
        "ix_intelligence_dataset_export_items_export_id",
        table_name="intelligence_dataset_export_items",
    )
    op.drop_table("intelligence_dataset_export_items")
    op.drop_index(
        "ix_intelligence_dataset_exports_dataset_type_status",
        table_name="intelligence_dataset_exports",
    )
    op.drop_index(
        "ix_intelligence_dataset_exports_workspace_created",
        table_name="intelligence_dataset_exports",
    )
    op.drop_table("intelligence_dataset_exports")
