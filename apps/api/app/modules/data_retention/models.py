from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class DataRetentionPolicyStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DataRetentionRunMode(StrEnum):
    DRY_RUN = "dry_run"
    APPLY = "apply"


class DataRetentionRunStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class DataRetentionTargetType(StrEnum):
    IMPORT_BATCH = "import_batch"
    LIVE_FEED_EVENT = "live_feed_event"
    PROVIDER_POLLING_REQUEST = "provider_polling_request"
    LLM_EXPLANATION_PAYLOAD = "llm_explanation_payload"
    REASONING_RUN_PAYLOAD = "reasoning_run_payload"
    DATASET_EXPORT = "dataset_export"
    WEBHOOK_OUTBOX_EVENT = "webhook_outbox_event"
    CHART_SCREENSHOT_AUDIT_PAYLOAD = "chart_screenshot_audit_payload"


class DataRetentionActionType(StrEnum):
    ARCHIVE = "archive"
    REDACT_PAYLOAD = "redact_payload"
    DELETE_RAW_PAYLOAD = "delete_raw_payload"
    DELETE_RECORD = "delete_record"
    NO_ACTION = "no_action"


class DataRetentionRunItemStatus(StrEnum):
    PLANNED = "planned"
    APPLIED = "applied"
    SKIPPED = "skipped"
    FAILED = "failed"


class DataRetentionPolicy(Base):
    __tablename__ = "data_retention_policies"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'paused', 'archived')",
            name="data_retention_policies_status_allowed",
        ),
        Index("ix_data_retention_policies_workspace_status", "workspace_id", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    policy_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class DataRetentionRun(Base):
    __tablename__ = "data_retention_runs"
    __table_args__ = (
        CheckConstraint(
            "mode in ('dry_run', 'apply')",
            name="data_retention_runs_mode_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'completed', 'completed_with_warnings', 'failed')",
            name="data_retention_runs_status_allowed",
        ),
        CheckConstraint("planned_action_count >= 0", name="planned_action_count_non_negative"),
        CheckConstraint("applied_action_count >= 0", name="applied_action_count_non_negative"),
        CheckConstraint("skipped_action_count >= 0", name="skipped_action_count_non_negative"),
        CheckConstraint("failed_action_count >= 0", name="failed_action_count_non_negative"),
        Index("ix_data_retention_runs_workspace_created", "workspace_id", "created_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_retention_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    planned_action_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    applied_action_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    skipped_action_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    failed_action_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    summary: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class DataRetentionRunItem(Base):
    __tablename__ = "data_retention_run_items"
    __table_args__ = (
        CheckConstraint(
            "target_type in ('import_batch', 'live_feed_event', 'provider_polling_request', "
            "'llm_explanation_payload', 'reasoning_run_payload', 'dataset_export', "
            "'webhook_outbox_event', 'chart_screenshot_audit_payload')",
            name="data_retention_run_items_target_type_allowed",
        ),
        CheckConstraint(
            "action_type in ('archive', 'redact_payload', 'delete_raw_payload', "
            "'delete_record', 'no_action')",
            name="data_retention_run_items_action_type_allowed",
        ),
        CheckConstraint(
            "status in ('planned', 'applied', 'skipped', 'failed')",
            name="data_retention_run_items_status_allowed",
        ),
        Index("ix_data_retention_run_items_retention_run_id", "retention_run_id"),
        Index("ix_data_retention_run_items_target", "target_type", "target_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    retention_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("data_retention_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(48), nullable=False)
    target_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
