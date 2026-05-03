"""add intelligence capabilities

Revision ID: 202605031000_intelligence_capabilities
Revises: 202605021500_scalable_engines_merge
Create Date: 2026-05-03 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "202605031000_intelligence_capabilities"
down_revision: str | Sequence[str] | None = "202605021500_scalable_engines_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intelligence_capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_type", sa.String(length=40), nullable=False),
        sa.Column("safety_level", sa.String(length=40), nullable=False),
        sa.Column("requires_external_credentials", sa.Boolean(), nullable=False),
        sa.Column("requires_database", sa.Boolean(), nullable=False),
        sa.Column(
            "input_contracts_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "output_contracts_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "produced_artifacts_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "route_refs_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "dependencies_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
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
            "category in ('ingestion', 'analysis', 'signal', 'explanation', 'reasoning', "
            "'outcome', 'diagnostics', 'reporting', 'operations', 'safety', 'governance', "
            "'export')",
            name="intelligence_capabilities_category_allowed",
        ),
        sa.CheckConstraint(
            "status in ('available', 'unavailable', 'disabled', 'experimental', 'deprecated')",
            name="intelligence_capabilities_status_allowed",
        ),
        sa.CheckConstraint(
            "execution_type in ('read_only', 'deterministic_write', 'external_provider', "
            "'llm_provider', 'worker', 'manual_only')",
            name="intelligence_capabilities_execution_type_allowed",
        ),
        sa.CheckConstraint(
            "safety_level in ('safe_read', 'safe_backend_write', 'provider_backed', "
            "'review_required', 'restricted')",
            name="intelligence_capabilities_safety_level_allowed",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "key",
            "version",
            name="uq_intelligence_capabilities_key_version",
        ),
    )
    op.create_index(
        "ix_intelligence_capabilities_category_status",
        "intelligence_capabilities",
        ["category", "status"],
    )
    op.create_index(
        "ix_intelligence_capabilities_execution_type",
        "intelligence_capabilities",
        ["execution_type"],
    )
    op.create_index(
        "ix_intelligence_capabilities_safety_level",
        "intelligence_capabilities",
        ["safety_level"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_intelligence_capabilities_safety_level",
        table_name="intelligence_capabilities",
    )
    op.drop_index(
        "ix_intelligence_capabilities_execution_type",
        table_name="intelligence_capabilities",
    )
    op.drop_index(
        "ix_intelligence_capabilities_category_status",
        table_name="intelligence_capabilities",
    )
    op.drop_table("intelligence_capabilities")
