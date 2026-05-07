"""add equity data operations

Revision ID: 202605071200_equity_ops
Revises: 202605071100_equity_data
Create Date: 2026-05-07 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "202605071200_equity_ops"
down_revision: str | Sequence[str] | None = "202605071100_equity_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def nullable_timestamp_column(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=True)


def json_object_column(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
        nullable=False,
    )


JOB_TYPES_WITH_EQUITY = (
    "'import.csv', 'import.json', 'provider_polling.fetch', 'scan.run', "
    "'daily_workflow.run', 'outcome.evaluate', 'reasoning.generate', "
    "'notification.deliver', 'read_model.rebuild', 'backfill.item', "
    "'data_quality.run', 'retention.apply', 'llm.explain', 'report.build', "
    "'equity_data.operation'"
)


JOB_TYPES_WITHOUT_EQUITY = (
    "'import.csv', 'import.json', 'provider_polling.fetch', 'scan.run', "
    "'daily_workflow.run', 'outcome.evaluate', 'reasoning.generate', "
    "'notification.deliver', 'read_model.rebuild', 'backfill.item', "
    "'data_quality.run', 'retention.apply', 'llm.explain', 'report.build'"
)


def upgrade() -> None:
    op.create_table(
        "equity_data_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=240), nullable=True),
        sa.Column("progress_current", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("progress_total", sa.Integer(), nullable=True),
        sa.Column("progress_message", sa.Text(), nullable=True),
        json_object_column("counters_json"),
        json_object_column("request_summary_json"),
        json_object_column("result_summary_json"),
        json_object_column("error_summary_json"),
        sa.Column("linked_provider_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("linked_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        nullable_timestamp_column("started_at"),
        nullable_timestamp_column("finished_at"),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.CheckConstraint(
            "operation_type in ('universe_import_rows', 'universe_import_file', "
            "'provider_universe_import', 'metadata_enrichment', 'fundamentals_enrichment', "
            "'earnings_enrichment', 'earnings_to_catalysts')",
            name="equity_data_operations_type_allowed",
        ),
        sa.CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="equity_data_operations_status_allowed",
        ),
        sa.CheckConstraint(
            "progress_current >= 0",
            name="equity_data_operations_progress_current_non_negative",
        ),
        sa.CheckConstraint(
            "progress_total is null or progress_total >= 0",
            name="equity_data_operations_progress_total_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["linked_job_id"],
            ["job_queue_items.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["linked_provider_request_id"],
            ["equity_data_provider_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_equity_data_operations_workspace_status_created",
        "equity_data_operations",
        ["workspace_id", "status", "created_at"],
    )
    op.create_index(
        "ix_equity_data_operations_workspace_type_created",
        "equity_data_operations",
        ["workspace_id", "operation_type", "created_at"],
    )
    op.create_index(
        "ix_equity_data_operations_provider",
        "equity_data_operations",
        ["provider_name"],
    )
    op.create_index(
        "ix_equity_data_operations_idempotency",
        "equity_data_operations",
        ["workspace_id", "idempotency_key"],
    )
    op.drop_constraint(
        "job_queue_definitions_job_type_allowed",
        "job_queue_definitions",
        type_="check",
    )
    op.create_check_constraint(
        "job_queue_definitions_job_type_allowed",
        "job_queue_definitions",
        f"job_type in ({JOB_TYPES_WITH_EQUITY})",
    )
    op.drop_constraint("job_queue_items_job_type_allowed", "job_queue_items", type_="check")
    op.create_check_constraint(
        "job_queue_items_job_type_allowed",
        "job_queue_items",
        f"job_type in ({JOB_TYPES_WITH_EQUITY})",
    )


def downgrade() -> None:
    op.drop_constraint(
        "job_queue_items_job_type_allowed",
        "job_queue_items",
        type_="check",
    )
    op.create_check_constraint(
        "job_queue_items_job_type_allowed",
        "job_queue_items",
        f"job_type in ({JOB_TYPES_WITHOUT_EQUITY})",
    )
    op.drop_constraint(
        "job_queue_definitions_job_type_allowed",
        "job_queue_definitions",
        type_="check",
    )
    op.create_check_constraint(
        "job_queue_definitions_job_type_allowed",
        "job_queue_definitions",
        f"job_type in ({JOB_TYPES_WITHOUT_EQUITY})",
    )
    op.drop_index("ix_equity_data_operations_idempotency", table_name="equity_data_operations")
    op.drop_index("ix_equity_data_operations_provider", table_name="equity_data_operations")
    op.drop_index(
        "ix_equity_data_operations_workspace_type_created",
        table_name="equity_data_operations",
    )
    op.drop_index(
        "ix_equity_data_operations_workspace_status_created",
        table_name="equity_data_operations",
    )
    op.drop_table("equity_data_operations")
