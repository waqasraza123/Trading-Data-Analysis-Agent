from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class StrategyProfileDraftStatus(StrEnum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ARCHIVED = "archived"


class StrategyProfileDraftValidationStatus(StrEnum):
    NOT_VALIDATED = "not_validated"
    VALID = "valid"
    VALID_WITH_WARNINGS = "valid_with_warnings"
    INVALID = "invalid"


class StrategyProfileDraftEventType(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    SUBMITTED_FOR_REVIEW = "submitted_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ARCHIVED = "archived"
    NOTE_ADDED = "note_added"


class StrategyProfileDraft(Base):
    __tablename__ = "strategy_profile_drafts"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft', 'ready_for_review', 'approved', 'rejected', "
            "'promoted', 'archived')",
            name="strategy_profile_drafts_status_allowed",
        ),
        CheckConstraint(
            "validation_status in ('not_validated', 'valid', 'valid_with_warnings', 'invalid')",
            name="strategy_profile_drafts_validation_status_allowed",
        ),
        Index("ix_strategy_profile_drafts_workspace_status", "workspace_id", "status"),
        Index("ix_strategy_profile_drafts_key_version", "draft_key", "draft_version"),
        Index(
            "ix_strategy_profile_drafts_base_strategy_profile_key",
            "base_strategy_profile_key",
        ),
        Index(
            "ix_strategy_profile_drafts_promoted_strategy_profile_id",
            "promoted_strategy_profile_id",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    base_strategy_profile_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    base_strategy_profile_key: Mapped[str] = mapped_column(String(80), nullable=False)
    base_strategy_profile_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    draft_key: Mapped[str] = mapped_column(String(80), nullable=False)
    draft_version: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    proposed_config_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_errors_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    validation_warnings_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    diff_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    simulation_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    diagnostic_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profile_diagnostic_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
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
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejected_by_user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    promoted_strategy_profile_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StrategyProfileDraftEvent(Base):
    __tablename__ = "strategy_profile_draft_events"
    __table_args__ = (
        CheckConstraint(
            "event_type in ('created', 'validated', 'submitted_for_review', 'approved', "
            "'rejected', 'promoted', 'archived', 'note_added')",
            name="strategy_profile_draft_events_event_type_allowed",
        ),
        Index("ix_strategy_profile_draft_events_draft_id", "draft_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    draft_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("strategy_profile_drafts.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
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
