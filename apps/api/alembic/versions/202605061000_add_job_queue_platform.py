"""add job queue platform

Revision ID: 202605061000_job_queue
Revises: 202605051100_workspace_setup
Create Date: 2026-05-06 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605061000_job_queue"
down_revision: str | Sequence[str] | None = "202605051100_workspace_setup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_queue_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("queue_name", sa.String(length=120), nullable=False),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("default_priority", sa.String(length=16), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
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
            "status in ('active', 'disabled', 'deprecated')",
            name="job_queue_definitions_status_allowed",
        ),
        sa.CheckConstraint(
            "job_type in ('import.csv', 'import.json', 'provider_polling.fetch', 'scan.run', "
            "'daily_workflow.run', 'outcome.evaluate', 'reasoning.generate', "
            "'notification.deliver', 'read_model.rebuild', 'backfill.item', "
            "'data_quality.run', 'retention.apply', 'llm.explain', 'report.build')",
            name="job_queue_definitions_job_type_allowed",
        ),
        sa.CheckConstraint(
            "default_priority in ('low', 'normal', 'high', 'urgent')",
            name="job_queue_definitions_priority_allowed",
        ),
        sa.CheckConstraint(
            "max_attempts > 0",
            name="job_queue_definitions_max_attempts_positive",
        ),
        sa.CheckConstraint(
            "timeout_seconds is null or timeout_seconds > 0",
            name="job_queue_definitions_timeout_positive",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_queue_definitions_key", "job_queue_definitions", ["key"], unique=True)
    op.create_index(
        "ix_job_queue_definitions_queue_status",
        "job_queue_definitions",
        ["queue_name", "status"],
    )
    op.create_index(
        "ix_job_queue_definitions_job_type_status",
        "job_queue_definitions",
        ["job_type", "status"],
    )
    op.create_table(
        "job_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("queue_name", sa.String(length=120), nullable=False),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("idempotency_key", sa.String(length=240), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=160), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('pending', 'scheduled', 'running', 'completed', "
            "'completed_with_warnings', 'retrying', 'failed', 'cancelled', 'dead_letter')",
            name="job_queue_items_status_allowed",
        ),
        sa.CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="job_queue_items_priority_allowed",
        ),
        sa.CheckConstraint(
            "job_type in ('import.csv', 'import.json', 'provider_polling.fetch', 'scan.run', "
            "'daily_workflow.run', 'outcome.evaluate', 'reasoning.generate', "
            "'notification.deliver', 'read_model.rebuild', 'backfill.item', "
            "'data_quality.run', 'retention.apply', 'llm.explain', 'report.build')",
            name="job_queue_items_job_type_allowed",
        ),
        sa.CheckConstraint("attempts >= 0", name="job_queue_items_attempts_non_negative"),
        sa.CheckConstraint("max_attempts > 0", name="job_queue_items_max_attempts_positive"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_queue_items_queue_status_priority_available",
        "job_queue_items",
        ["queue_name", "status", "priority", "available_at"],
    )
    op.create_index(
        "ix_job_queue_items_workspace_status",
        "job_queue_items",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_job_queue_items_job_type_status",
        "job_queue_items",
        ["job_type", "status"],
    )
    op.create_index(
        "ix_job_queue_items_lock",
        "job_queue_items",
        ["locked_by", "locked_until"],
    )
    op.create_index(
        "uq_job_queue_items_workspace_idempotency_key",
        "job_queue_items",
        ["workspace_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("workspace_id is not null and idempotency_key is not null"),
    )
    op.create_index(
        "uq_job_queue_items_global_idempotency_key",
        "job_queue_items",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("workspace_id is null and idempotency_key is not null"),
    )
    op.create_table(
        "job_queue_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            "event_type in ('enqueued', 'claimed', 'started', 'heartbeat', 'completed', "
            "'failed', 'retry_scheduled', 'cancelled', 'dead_lettered')",
            name="job_queue_events_event_type_allowed",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["job_queue_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_job_queue_events_job_id", "job_queue_events", ["job_id"])
    op.create_index(
        "ix_job_queue_events_workspace_created",
        "job_queue_events",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_queue_events_workspace_created", table_name="job_queue_events")
    op.drop_index("ix_job_queue_events_job_id", table_name="job_queue_events")
    op.drop_table("job_queue_events")
    op.drop_index("uq_job_queue_items_global_idempotency_key", table_name="job_queue_items")
    op.drop_index("uq_job_queue_items_workspace_idempotency_key", table_name="job_queue_items")
    op.drop_index("ix_job_queue_items_lock", table_name="job_queue_items")
    op.drop_index("ix_job_queue_items_job_type_status", table_name="job_queue_items")
    op.drop_index("ix_job_queue_items_workspace_status", table_name="job_queue_items")
    op.drop_index(
        "ix_job_queue_items_queue_status_priority_available",
        table_name="job_queue_items",
    )
    op.drop_table("job_queue_items")
    op.drop_index("ix_job_queue_definitions_job_type_status", table_name="job_queue_definitions")
    op.drop_index("ix_job_queue_definitions_queue_status", table_name="job_queue_definitions")
    op.drop_index("ix_job_queue_definitions_key", table_name="job_queue_definitions")
    op.drop_table("job_queue_definitions")
