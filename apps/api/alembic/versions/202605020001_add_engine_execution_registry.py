"""add engine execution registry

Revision ID: 202605020001
Revises: 202604301900
Create Date: 2026-05-02 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605020001"
down_revision: str | Sequence[str] | None = "202604301900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "engine_execution_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine_name", sa.String(length=120), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=True),
        sa.Column("operation_type", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=240), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "produced_artifacts_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("locked_by", sa.String(length=160), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'skipped', 'failed', 'cancelled')",
            name="engine_execution_records_status_allowed",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high')",
            name="engine_execution_records_priority_allowed",
        ),
        sa.CheckConstraint(
            "attempts >= 0",
            name="engine_execution_records_attempts_non_negative",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="engine_execution_records_max_attempts_positive",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_engine_execution_records_workspace_id_idempotency_key",
        ),
    )
    op.create_index(
        "ix_engine_execution_records_workspace_status_created",
        "engine_execution_records",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_engine_execution_records_engine_operation",
        "engine_execution_records",
        ["engine_name", "operation_type"],
    )
    op.create_index(
        "ix_engine_execution_records_source",
        "engine_execution_records",
        ["source_type", "source_id"],
    )
    op.create_index(
        "ix_engine_execution_records_lock",
        "engine_execution_records",
        ["locked_by", "locked_until"],
    )
    op.create_table(
        "engine_execution_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("execution_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "event_type in ('created', 'claimed', 'started', 'completed', 'skipped', "
            "'failed', 'retry_scheduled', 'cancelled', 'artifact_recorded')",
            name="engine_execution_events_event_type_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["execution_record_id"],
            ["engine_execution_records.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_engine_execution_events_execution_record_id",
        "engine_execution_events",
        ["execution_record_id"],
    )
    op.create_index(
        "ix_engine_execution_events_workspace_created",
        "engine_execution_events",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_engine_execution_events_workspace_created",
        table_name="engine_execution_events",
    )
    op.drop_index(
        "ix_engine_execution_events_execution_record_id",
        table_name="engine_execution_events",
    )
    op.drop_table("engine_execution_events")
    op.drop_index("ix_engine_execution_records_lock", table_name="engine_execution_records")
    op.drop_index("ix_engine_execution_records_source", table_name="engine_execution_records")
    op.drop_index(
        "ix_engine_execution_records_engine_operation",
        table_name="engine_execution_records",
    )
    op.drop_index(
        "ix_engine_execution_records_workspace_status_created",
        table_name="engine_execution_records",
    )
    op.drop_table("engine_execution_records")
