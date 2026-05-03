"""state machine registry

Revision ID: 202605020980_state_machine_registry
Revises: f9eb9423c4a2
Create Date: 2026-05-02 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020980_state_machine_registry"
down_revision: str | tuple[str, str] | None = "f9eb9423c4a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "state_machine_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("object_type", sa.String(length=120), nullable=False),
        sa.Column("states_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("transitions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("terminal_states_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status in ('active', 'draft', 'archived')",
            name=op.f("ck_state_machine_definitions_state_machine_definitions_status_allowed"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_state_machine_definitions")),
        sa.UniqueConstraint("key", "version", name="uq_state_machine_definitions_key_version"),
    )
    op.create_index(
        "ix_state_machine_definitions_key",
        "state_machine_definitions",
        ["key"],
        unique=False,
    )
    op.create_index(
        "ix_state_machine_definitions_object_type",
        "state_machine_definitions",
        ["object_type"],
        unique=False,
    )
    op.create_index(
        "ix_state_machine_definitions_status",
        "state_machine_definitions",
        ["status"],
        unique=False,
    )
    op.create_table(
        "state_transition_validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state_machine_key", sa.String(length=120), nullable=False),
        sa.Column("state_machine_version", sa.String(length=40), nullable=False),
        sa.Column("object_type", sa.String(length=120), nullable=False),
        sa.Column("object_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_state", sa.String(length=80), nullable=False),
        sa.Column("to_state", sa.String(length=80), nullable=False),
        sa.Column("validation_status", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "validation_status in ('valid', 'invalid')",
            name=op.f("ck_state_transition_validations_state_transition_validations_status_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_state_transition_validations_workspace_id_workspaces"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_state_transition_validations")),
    )
    op.create_index(
        "ix_state_transition_validations_machine",
        "state_transition_validations",
        ["state_machine_key", "state_machine_version"],
        unique=False,
    )
    op.create_index(
        "ix_state_transition_validations_object",
        "state_transition_validations",
        ["object_type", "object_id"],
        unique=False,
    )
    op.create_index(
        "ix_state_transition_validations_status",
        "state_transition_validations",
        ["validation_status"],
        unique=False,
    )
    op.create_index(
        "ix_state_transition_validations_workspace_created",
        "state_transition_validations",
        ["workspace_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_state_transition_validations_workspace_created",
        table_name="state_transition_validations",
    )
    op.drop_index("ix_state_transition_validations_status", table_name="state_transition_validations")
    op.drop_index("ix_state_transition_validations_object", table_name="state_transition_validations")
    op.drop_index("ix_state_transition_validations_machine", table_name="state_transition_validations")
    op.drop_table("state_transition_validations")
    op.drop_index("ix_state_machine_definitions_status", table_name="state_machine_definitions")
    op.drop_index("ix_state_machine_definitions_object_type", table_name="state_machine_definitions")
    op.drop_index("ix_state_machine_definitions_key", table_name="state_machine_definitions")
    op.drop_table("state_machine_definitions")
