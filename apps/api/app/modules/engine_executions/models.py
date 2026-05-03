from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class EngineExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    SKIPPED = "skipped"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EngineExecutionPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class EngineExecutionEventType(StrEnum):
    CREATED = "created"
    CLAIMED = "claimed"
    STARTED = "started"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"
    RETRY_SCHEDULED = "retry_scheduled"
    CANCELLED = "cancelled"
    ARTIFACT_RECORDED = "artifact_recorded"


class EngineExecutionRecord(Base):
    __tablename__ = "engine_execution_records"
    __table_args__ = (
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'skipped', 'failed', 'cancelled')",
            name="engine_execution_records_status_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high')",
            name="engine_execution_records_priority_allowed",
        ),
        CheckConstraint("attempts >= 0", name="engine_execution_records_attempts_non_negative"),
        CheckConstraint("max_attempts > 0", name="engine_execution_records_max_attempts_positive"),
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_engine_execution_records_workspace_id_idempotency_key",
        ),
        Index(
            "ix_engine_execution_records_workspace_status_created",
            "workspace_id",
            "status",
            "created_at",
        ),
        Index(
            "ix_engine_execution_records_engine_operation",
            "engine_name",
            "operation_type",
        ),
        Index(
            "ix_engine_execution_records_source",
            "source_type",
            "source_id",
        ),
        Index(
            "ix_engine_execution_records_lock",
            "locked_by",
            "locked_until",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    engine_name: Mapped[str] = mapped_column(String(120), nullable=False)
    engine_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(120), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    produced_artifacts_json: Mapped[list[dict[str, object]] | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    locked_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class EngineExecutionEvent(Base):
    __tablename__ = "engine_execution_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('created', 'claimed', 'started', 'completed', 'skipped', "
            "'failed', 'retry_scheduled', 'cancelled', 'artifact_recorded')",
            name="engine_execution_events_event_type_allowed",
        ),
        Index(
            "ix_engine_execution_events_execution_record_id",
            "execution_record_id",
        ),
        Index(
            "ix_engine_execution_events_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    execution_record_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("engine_execution_records.id", ondelete="CASCADE"),
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
