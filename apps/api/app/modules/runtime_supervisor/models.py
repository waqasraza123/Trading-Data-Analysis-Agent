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


class RuntimeWorkerType(StrEnum):
    LIVE_FEED = "live_feed"
    STALE_MONITOR = "stale_monitor"
    REASONING_ACTIONS = "reasoning_actions"
    MARKET_SCANS = "market_scans"
    PROVIDER_POLLING = "provider_polling"
    NOTIFICATION_DELIVERY = "notification_delivery"
    DATA_RETENTION = "data_retention"
    BACKFILL = "backfill"
    METRICS = "metrics"
    CUSTOM = "custom"


class RuntimeWorkerDefinitionStatus(StrEnum):
    AVAILABLE = "available"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    UNAVAILABLE = "unavailable"


class RuntimeWorkerInstanceStatus(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    STALE = "stale"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class RuntimeRunRequestType(StrEnum):
    RUN_ONCE = "run_once"
    EXECUTE_DUE = "execute_due"
    REFRESH_STATUS = "refresh_status"
    DRY_RUN = "dry_run"


class RuntimeRunRequestStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNSUPPORTED = "unsupported"


class RuntimeWorkerDefinition(Base):
    __tablename__ = "runtime_worker_definitions"
    __table_args__ = (
        CheckConstraint(
            "worker_type in ('live_feed', 'stale_monitor', 'reasoning_actions', "
            "'market_scans', 'provider_polling', 'notification_delivery', "
            "'data_retention', 'backfill', 'metrics', 'custom')",
            name="runtime_worker_definitions_worker_type_allowed",
        ),
        CheckConstraint(
            "status in ('available', 'disabled', 'deprecated', 'unavailable')",
            name="runtime_worker_definitions_status_allowed",
        ),
        UniqueConstraint("key", name="uq_runtime_worker_definitions_key"),
        Index("ix_runtime_worker_definitions_key_status", "key", "status"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    worker_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    command: Mapped[str] = mapped_column(String(240), nullable=False)
    required_settings_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    optional_settings_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    safety_notes_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class RuntimeWorkerInstance(Base):
    __tablename__ = "runtime_worker_instances"
    __table_args__ = (
        CheckConstraint(
            "status in ('starting', 'running', 'stale', 'stopped', 'failed', 'unknown')",
            name="runtime_worker_instances_status_allowed",
        ),
        UniqueConstraint("worker_id", name="uq_runtime_worker_instances_worker_id"),
        Index(
            "ix_runtime_worker_instances_definition_status",
            "worker_definition_key",
            "status",
        ),
        Index("ix_runtime_worker_instances_last_heartbeat_at", "last_heartbeat_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    worker_definition_key: Mapped[str] = mapped_column(
        String(120),
        ForeignKey("runtime_worker_definitions.key", ondelete="RESTRICT"),
        nullable=False,
    )
    worker_id: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    host_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    process_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_payload_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class RuntimeWorkerRunRequest(Base):
    __tablename__ = "runtime_worker_run_requests"
    __table_args__ = (
        CheckConstraint(
            "request_type in ('run_once', 'execute_due', 'refresh_status', 'dry_run')",
            name="runtime_worker_run_requests_request_type_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled', 'unsupported')",
            name="runtime_worker_run_requests_status_allowed",
        ),
        Index(
            "ix_runtime_worker_run_requests_definition_status",
            "worker_definition_key",
            "status",
        ),
        Index(
            "ix_runtime_worker_run_requests_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    worker_definition_key: Mapped[str] = mapped_column(
        String(120),
        ForeignKey("runtime_worker_definitions.key", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    request_type: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
