from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, uuid_primary_key


class IntelligenceMetricSnapshotType(StrEnum):
    WORKSPACE = "workspace"
    GLOBAL = "global"
    MODULE = "module"
    OPERATIONAL_HEALTH = "operational_health"


class IntelligenceMetricSnapshotStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class IntelligenceMetricSnapshot(Base):
    __tablename__ = "intelligence_metric_snapshots"
    __table_args__ = (
        CheckConstraint(
            "snapshot_type in ('workspace', 'global', 'module', 'operational_health')",
            name="intelligence_metric_snapshots_snapshot_type_allowed",
        ),
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="intelligence_metric_snapshots_status_allowed",
        ),
        Index(
            "ix_intelligence_metric_snapshots_workspace_collected",
            "workspace_id",
            "collected_at",
        ),
        Index(
            "ix_intelligence_metric_snapshots_type_collected",
            "snapshot_type",
            "collected_at",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at = created_at_column()
