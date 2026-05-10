"""add runtime supervisor

Revision ID: 202605050900_runtime_supervisor
Revises: 202605032000_daily_product_workflow_merge
Create Date: 2026-05-05 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605050900_runtime_supervisor"
down_revision: str | Sequence[str] | None = "202605032000_daily_product_workflow_merge"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runtime_worker_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("worker_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("command", sa.String(length=240), nullable=False),
        sa.Column(
            "required_settings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "optional_settings_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "safety_notes_json",
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
            "worker_type in ('live_feed', 'stale_monitor', 'reasoning_actions', "
            "'market_scans', 'provider_polling', 'notification_delivery', "
            "'data_retention', 'backfill', 'metrics', 'custom')",
            name="runtime_worker_definitions_worker_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('available', 'disabled', 'deprecated', 'unavailable')",
            name="runtime_worker_definitions_status_allowed",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_runtime_worker_definitions_key"),
    )
    op.create_index(
        "ix_runtime_worker_definitions_key_status",
        "runtime_worker_definitions",
        ["key", "status"],
    )
    op.create_table(
        "runtime_worker_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("worker_definition_key", sa.String(length=120), nullable=False),
        sa.Column("worker_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("host_name", sa.String(length=160), nullable=True),
        sa.Column("process_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "heartbeat_payload_json",
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
            "status in ('starting', 'running', 'stale', 'stopped', 'failed', 'unknown')",
            name="runtime_worker_instances_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["worker_definition_key"],
            ["runtime_worker_definitions.key"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id", name="uq_runtime_worker_instances_worker_id"),
    )
    op.create_index(
        "ix_runtime_worker_instances_definition_status",
        "runtime_worker_instances",
        ["worker_definition_key", "status"],
    )
    op.create_index(
        "ix_runtime_worker_instances_last_heartbeat_at",
        "runtime_worker_instances",
        ["last_heartbeat_at"],
    )
    op.create_table(
        "runtime_worker_run_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("worker_definition_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column(
            "input_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
            "request_type in ('run_once', 'execute_due', 'refresh_status', 'dry_run')",
            name="runtime_worker_run_requests_request_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled', 'unsupported')",
            name="runtime_worker_run_requests_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["worker_definition_key"],
            ["runtime_worker_definitions.key"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_worker_run_requests_definition_status",
        "runtime_worker_run_requests",
        ["worker_definition_key", "status"],
    )
    op.create_index(
        "ix_runtime_worker_run_requests_workspace_created",
        "runtime_worker_run_requests",
        ["workspace_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_runtime_worker_run_requests_workspace_created",
        table_name="runtime_worker_run_requests",
    )
    op.drop_index(
        "ix_runtime_worker_run_requests_definition_status",
        table_name="runtime_worker_run_requests",
    )
    op.drop_table("runtime_worker_run_requests")
    op.drop_index(
        "ix_runtime_worker_instances_last_heartbeat_at",
        table_name="runtime_worker_instances",
    )
    op.drop_index(
        "ix_runtime_worker_instances_definition_status",
        table_name="runtime_worker_instances",
    )
    op.drop_table("runtime_worker_instances")
    op.drop_index(
        "ix_runtime_worker_definitions_key_status",
        table_name="runtime_worker_definitions",
    )
    op.drop_table("runtime_worker_definitions")
