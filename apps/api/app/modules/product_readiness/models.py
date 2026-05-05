from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ProductReadinessRunStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class ProductReadinessLabel(StrEnum):
    READY = "ready"
    NEEDS_SETUP = "needs_setup"
    DEGRADED = "degraded"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class ProductReadinessCheckStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


class ProductReadinessRun(Base):
    __tablename__ = "product_readiness_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="product_readiness_runs_status_allowed",
        ),
        CheckConstraint(
            "readiness_label in ('ready', 'needs_setup', 'degraded', 'blocked', 'unknown')",
            name="product_readiness_runs_label_allowed",
        ),
        CheckConstraint(
            "readiness_score >= 0 and readiness_score <= 1",
            name="product_readiness_runs_score_range",
        ),
        Index(
            "ix_product_readiness_runs_workspace_created",
            "workspace_id",
            "created_at",
        ),
        Index("ix_product_readiness_runs_readiness_label", "readiness_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    readiness_version: Mapped[str] = mapped_column(String(40), nullable=False)
    readiness_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    readiness_label: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    checks_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    blockers_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
