from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class OperatorReviewSourceType(StrEnum):
    CHART_SCREENSHOT_RUN = "chart_screenshot_run"
    SIGNAL = "signal"
    ANALYSIS_RUN = "analysis_run"
    REASONING_RUN = "reasoning_run"
    ACTION_ITEM = "action_item"
    QUALITY_FINDING = "quality_finding"
    CALIBRATION_RECOMMENDATION = "calibration_recommendation"
    OUTCOME = "outcome"
    MANUAL = "manual"


class OperatorReviewType(StrEnum):
    EXTRACTION_QUALITY = "extraction_quality"
    SIGNAL_QUALITY = "signal_quality"
    SHADOW_DISAGREEMENT = "shadow_disagreement"
    UNSAFE_LLM_OUTPUT = "unsafe_llm_output"
    CALIBRATION_REVIEW = "calibration_review"
    ACTION_REVIEW = "action_review"
    OUTCOME_REVIEW = "outcome_review"
    MANUAL_REVIEW = "manual_review"


class OperatorReviewPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class OperatorReviewStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    CANCELLED = "cancelled"


class OperatorReviewResolution(StrEnum):
    ACCEPTED = "accepted"
    CORRECTED = "corrected"
    DISMISSED = "dismissed"
    NEEDS_MORE_DATA = "needs_more_data"
    NO_ACTION = "no_action"
    ESCALATED = "escalated"


class OperatorReviewEventType(StrEnum):
    CREATED = "created"
    ASSIGNED = "assigned"
    STATUS_CHANGED = "status_changed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
    ESCALATED = "escalated"
    NOTE_ADDED = "note_added"


class OperatorReviewItem(Base):
    __tablename__ = "operator_review_items"
    __table_args__ = (
        CheckConstraint(
            "source_type in ('chart_screenshot_run', 'signal', 'analysis_run', "
            "'reasoning_run', 'action_item', 'quality_finding', "
            "'calibration_recommendation', 'outcome', 'manual')",
            name="operator_review_items_source_type_allowed",
        ),
        CheckConstraint(
            "review_type in ('extraction_quality', 'signal_quality', "
            "'shadow_disagreement', 'unsafe_llm_output', 'calibration_review', "
            "'action_review', 'outcome_review', 'manual_review')",
            name="operator_review_items_review_type_allowed",
        ),
        CheckConstraint(
            "priority in ('low', 'normal', 'high', 'urgent')",
            name="operator_review_items_priority_allowed",
        ),
        CheckConstraint(
            "status in ('open', 'assigned', 'in_review', 'resolved', 'dismissed', "
            "'cancelled')",
            name="operator_review_items_status_allowed",
        ),
        CheckConstraint(
            "resolution is null or resolution in ('accepted', 'corrected', 'dismissed', "
            "'needs_more_data', 'no_action', 'escalated')",
            name="operator_review_items_resolution_allowed",
        ),
        Index(
            "ix_operator_review_items_workspace_status_priority",
            "workspace_id",
            "status",
            "priority",
        ),
        Index("ix_operator_review_items_source", "source_type", "source_id"),
        Index("ix_operator_review_items_related_signal_id", "related_signal_id"),
        Index("ix_operator_review_items_related_analysis_run_id", "related_analysis_run_id"),
        Index(
            "ix_operator_review_items_assigned_status",
            "assigned_to_user_id",
            "status",
        ),
        Index("ix_operator_review_items_review_type_status", "review_type", "status"),
        Index(
            "uq_operator_review_items_active_source_review",
            "workspace_id",
            "source_type",
            "source_id",
            "review_type",
            unique=True,
            postgresql_where=text("status in ('open', 'assigned', 'in_review')"),
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(48), nullable=False)
    source_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    related_analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_reasoning_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("llm_reasoning_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_action_item_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("reasoning_action_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_type: Mapped[str] = mapped_column(String(40), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    assigned_to_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class OperatorReviewEvent(Base):
    __tablename__ = "operator_review_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('created', 'assigned', 'status_changed', 'resolved', "
            "'dismissed', 'escalated', 'note_added')",
            name="operator_review_events_event_type_allowed",
        ),
        Index("ix_operator_review_events_review_item_id", "review_item_id"),
        Index("ix_operator_review_events_workspace_created", "workspace_id", "created_at"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    review_item_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("operator_review_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
