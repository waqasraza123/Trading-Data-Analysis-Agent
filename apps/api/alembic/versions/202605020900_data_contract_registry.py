"""add data contract registry

Revision ID: 202605020920_data_contract_registry
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020920_data_contract_registry"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column(
            "schema_json",
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
            "status in ('active', 'draft', 'deprecated', 'archived')",
            name=op.f("ck_data_contracts_data_contracts_status_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_contracts")),
        sa.UniqueConstraint("key", "version", name="uq_data_contracts_key_version"),
    )
    op.create_index(
        "ix_data_contracts_key_version_status",
        "data_contracts",
        ["key", "version", "status"],
    )
    op.create_table(
        "data_contract_validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("contract_key", sa.String(length=120), nullable=False),
        sa.Column("contract_version", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=120), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "validation_errors_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "validation_warnings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "payload_summary_json",
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
            "status in ('passed', 'failed', 'passed_with_warnings')",
            name=op.f("ck_data_contract_validations_data_contract_validations_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_data_contract_validations_workspace_id_workspaces"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_data_contract_validations")),
    )
    op.create_index(
        "ix_data_contract_validations_source_type_source_id",
        "data_contract_validations",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_data_contract_validations_contract_status",
        "data_contract_validations",
        ["contract_key", "contract_version", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_data_contract_validations_contract_status",
        table_name="data_contract_validations",
    )
    op.drop_index(
        "ix_data_contract_validations_source_type_source_id",
        table_name="data_contract_validations",
    )
    op.drop_table("data_contract_validations")
    op.drop_index("ix_data_contracts_key_version_status", table_name="data_contracts")
    op.drop_table("data_contracts")
