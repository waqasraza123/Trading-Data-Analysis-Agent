from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, uuid_primary_key


class ServiceSloSnapshotStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    UNKNOWN = "unknown"


class ServiceSloSnapshot(Base):
    __tablename__ = "service_slo_snapshots"
    __table_args__ = (
        CheckConstraint(
            "status in ('healthy', 'degraded', 'failing', 'unknown')",
            name="service_slo_snapshots_status_allowed",
        ),
        Index(
            "ix_service_slo_snapshots_workspace_created",
            "workspace_id",
            "created_at",
        ),
        Index("ix_service_slo_snapshots_status", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    slo_version: Mapped[str] = mapped_column(String(32), nullable=False)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
