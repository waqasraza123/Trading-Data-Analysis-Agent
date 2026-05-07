from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class JobQueueDefinitionStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class JobQueueItemStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class JobQueuePriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class JobQueueEventType(StrEnum):
    ENQUEUED = "enqueued"
    CLAIMED = "claimed"
    STARTED = "started"
    HEARTBEAT = "heartbeat"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"
    DEAD_LETTERED = "dead_lettered"


class JobQueueJobType(StrEnum):
    IMPORT_CSV = "import.csv"
    IMPORT_JSON = "import.json"
    PROVIDER_POLLING_FETCH = "provider_polling.fetch"
    SCAN_RUN = "scan.run"
    DAILY_WORKFLOW_RUN = "daily_workflow.run"
    OUTCOME_EVALUATE = "outcome.evaluate"
    REASONING_GENERATE = "reasoning.generate"
    NOTIFICATION_DELIVER = "notification.deliver"
    READ_MODEL_REBUILD = "read_model.rebuild"
    BACKFILL_ITEM = "backfill.item"
    DATA_QUALITY_RUN = "data_quality.run"
    RETENTION_APPLY = "retention.apply"
    LLM_EXPLAIN = "llm.explain"
    REPORT_BUILD = "report.build"
    EQUITY_DATA_OPERATION = "equity_data.operation"


class JobQueueDefinition(Base):
    __tablename__ = "job_queue_definitions"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'disabled', 'deprecated')",
            name="job_queue_definitions_status_allowed",
        ),
        CheckConstraint(
            "job_type in ('import.csv', 'import.json', 'provider_polling.fetch', 'scan.run', "
            "'daily_workflow.run', 'outcome.evaluate', 'reasoning.generate', "
            "'notification.deliver', 'read_model.rebuild', 'backfill.item', "
            "'data_quality.run', 'retention.apply', 'llm.explain', 'report.build', "
            "'equity_data.operation')",
            name="job_queue_definitions_job_type_allowed",
        ),
        CheckConstraint(
            "default_priority in ('low', 'normal', 'high', 'urgent')",
            name="job_queue_definitions_priority_allowed",
        ),
        CheckConstraint("max_attempts > 0", name="job_queue_definitions_max_attempts_positive"),
        CheckConstraint(
            "timeout_seconds is null or timeout_seconds > 0",
            name="job_queue_definitions_timeout_positive",
        ),
        Index("ix_job_queue_definitions_key", "key", unique=True),
        Index("ix_job_queue_definitions_queue_status", "queue_name", "status"),
        Index("ix_job_queue_definitions_job_type_status", "job_type", "status"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    queue_name: Mapped[str] = mapped_column(String(120), nullable=False)
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default=text("3"),
    )
    default_priority: Mapped[str] = mapped_column(String(16), nullable=False)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class JobQueueItem(Base):
    __tablename__ = "job_queue_items"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'scheduled', 'running', 'completed', "
            "'completed_with_warnings', 'retrying', 'failed', 'cancelled', 'dead_letter')",
            name="job_queue_items_status_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="job_queue_items_priority_allowed",
        ),
        CheckConstraint(
            "job_type in ('import.csv', 'import.json', 'provider_polling.fetch', 'scan.run', "
            "'daily_workflow.run', 'outcome.evaluate', 'reasoning.generate', "
            "'notification.deliver', 'read_model.rebuild', 'backfill.item', "
            "'data_quality.run', 'retention.apply', 'llm.explain', 'report.build', "
            "'equity_data.operation')",
            name="job_queue_items_job_type_allowed",
        ),
        CheckConstraint("attempts >= 0", name="job_queue_items_attempts_non_negative"),
        CheckConstraint("max_attempts > 0", name="job_queue_items_max_attempts_positive"),
        Index(
            "ix_job_queue_items_queue_status_priority_available",
            "queue_name",
            "status",
            "priority",
            "available_at",
        ),
        Index("ix_job_queue_items_workspace_status", "workspace_id", "status"),
        Index("ix_job_queue_items_job_type_status", "job_type", "status"),
        Index("ix_job_queue_items_lock", "locked_by", "locked_until"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    queue_name: Mapped[str] = mapped_column(String(120), nullable=False)
    job_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(240), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default=text("3"),
    )
    payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class JobQueueEvent(Base):
    __tablename__ = "job_queue_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('enqueued', 'claimed', 'started', 'heartbeat', 'completed', "
            "'failed', 'retry_scheduled', 'cancelled', 'dead_lettered')",
            name="job_queue_events_event_type_allowed",
        ),
        Index("ix_job_queue_events_job_id", "job_id"),
        Index("ix_job_queue_events_workspace_created", "workspace_id", "created_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("job_queue_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
