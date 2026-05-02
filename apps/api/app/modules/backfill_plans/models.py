from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class BackfillPlanType(StrEnum):
    MISSING_ARTIFACTS = "missing_artifacts"
    STALE_ARTIFACTS = "stale_artifacts"
    MODULE_BACKFILL = "module_backfill"
    OUTCOME_BACKFILL = "outcome_backfill"
    CONTEXT_BACKFILL = "context_backfill"
    QUALITY_BACKFILL = "quality_backfill"
    DATASET_BACKFILL = "dataset_backfill"


class BackfillPlanStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BackfillItemTargetType(StrEnum):
    ANALYSIS_RUN = "analysis_run"
    SIGNAL = "signal"
    OUTCOME = "outcome"
    REASONING_RUN = "reasoning_run"
    CHART_SCREENSHOT_RUN = "chart_screenshot_run"
    NEWS_EVENT = "news_event"
    WORKSPACE = "workspace"


class BackfillItemStatus(StrEnum):
    PLANNED = "planned"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackfillItemPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class IntelligenceBackfillPlan(Base):
    __tablename__ = "intelligence_backfill_plans"
    __table_args__ = (
        CheckConstraint(
            "plan_type in ('missing_artifacts', 'stale_artifacts', 'module_backfill', "
            "'outcome_backfill', 'context_backfill', 'quality_backfill', 'dataset_backfill')",
            name="intelligence_backfill_plans_plan_type_allowed",
        ),
        CheckConstraint(
            "status in ('draft', 'ready', 'completed', 'cancelled', 'failed')",
            name="intelligence_backfill_plans_status_allowed",
        ),
        CheckConstraint(
            "eligible_count >= 0 and planned_count >= 0 and skipped_count >= 0 "
            "and blocked_count >= 0",
            name="intelligence_backfill_plans_counts_non_negative",
        ),
        Index(
            "ix_intelligence_backfill_plans_workspace_type_status",
            "workspace_id",
            "plan_type",
            "status",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    plan_version: Mapped[str] = mapped_column(String(40), nullable=False)
    filters_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    target_module: Mapped[str] = mapped_column(String(80), nullable=False)
    target_operation: Mapped[str] = mapped_column(String(80), nullable=False)
    dry_run: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    eligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    planned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class IntelligenceBackfillItem(Base):
    __tablename__ = "intelligence_backfill_items"
    __table_args__ = (
        CheckConstraint(
            "target_type in ('analysis_run', 'signal', 'outcome', 'reasoning_run', "
            "'chart_screenshot_run', 'news_event', 'workspace')",
            name="intelligence_backfill_items_target_type_allowed",
        ),
        CheckConstraint(
            "status in ('planned', 'skipped', 'blocked', 'queued', 'completed', "
            "'failed', 'cancelled')",
            name="intelligence_backfill_items_status_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high')",
            name="intelligence_backfill_items_priority_allowed",
        ),
        UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_intelligence_backfill_items_workspace_idempotency_key",
        ),
        Index("ix_intelligence_backfill_items_plan_status", "backfill_plan_id", "status"),
        Index("ix_intelligence_backfill_items_target", "target_type", "target_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    backfill_plan_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("intelligence_backfill_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    target_operation: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(220), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    skip_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    block_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    execution_record_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
