from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class JournalEntryStatus(StrEnum):
    DRAFT = "draft"
    SAVED = "saved"
    ARCHIVED = "archived"


class JournalDecisionType(StrEnum):
    OBSERVED = "observed"
    IGNORED = "ignored"
    REVIEWED = "reviewed"
    PAPER_FOLLOWED = "paper_followed"
    EXTERNAL_ACTION_TAKEN = "external_action_taken"
    NO_ACTION = "no_action"
    UNCERTAIN = "uncertain"


class JournalUserBias(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    UNCLEAR = "unclear"


class JournalReflectionLabel(StrEnum):
    ALIGNED_WITH_OBSERVED_OUTCOME = "aligned_with_observed_outcome"
    CONFLICTED_WITH_OBSERVED_OUTCOME = "conflicted_with_observed_outcome"
    INCONCLUSIVE = "inconclusive"
    INSUFFICIENT_OUTCOME_DATA = "insufficient_outcome_data"
    NEEDS_MORE_REVIEW = "needs_more_review"


class JournalAttachmentType(StrEnum):
    CHART_SCREENSHOT = "chart_screenshot"
    SIGNAL_REPORT = "signal_report"
    AUDIT_TIMELINE = "audit_timeline"
    EXTERNAL_NOTE = "external_note"
    DATASET_REFERENCE = "dataset_reference"


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft', 'saved', 'archived')",
            name="journal_entries_status_allowed",
        ),
        CheckConstraint(
            "decision_type in ('observed', 'ignored', 'reviewed', 'paper_followed', "
            "'external_action_taken', 'no_action', 'uncertain')",
            name="journal_entries_decision_type_allowed",
        ),
        CheckConstraint(
            "user_bias is null or user_bias in ('bullish', 'bearish', 'neutral', 'unclear')",
            name="journal_entries_user_bias_allowed",
        ),
        CheckConstraint(
            "confidence_before is null or (confidence_before >= 0 and confidence_before <= 1)",
            name="journal_entries_confidence_before_range",
        ),
        Index("ix_journal_entries_workspace_created_at", "workspace_id", "created_at"),
        Index("ix_journal_entries_signal_id", "signal_id"),
        Index("ix_journal_entries_analysis_run_id", "analysis_run_id"),
        Index("ix_journal_entries_setup_context_id", "setup_context_id"),
        Index("ix_journal_entries_decision_type", "decision_type"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    analysis_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    setup_context_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("setup_contexts.id", ondelete="SET NULL"),
        nullable=True,
    )
    chart_screenshot_run_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("chart_screenshot_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    decision_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_before: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    user_bias: Mapped[str | None] = mapped_column(String(16), nullable=True)
    user_notes: Mapped[str] = mapped_column(Text, nullable=False)
    tags_json: Mapped[list[str]] = mapped_column(
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
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class JournalEntryReview(Base):
    __tablename__ = "journal_entry_reviews"
    __table_args__ = (
        CheckConstraint(
            "reflection_label in ('aligned_with_observed_outcome', "
            "'conflicted_with_observed_outcome', 'inconclusive', "
            "'insufficient_outcome_data', 'needs_more_review')",
            name="journal_entry_reviews_reflection_label_allowed",
        ),
        Index("ix_journal_entry_reviews_journal_entry_id", "journal_entry_id"),
        Index("ix_journal_entry_reviews_reflection_label", "reflection_label"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    journal_entry_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    outcome_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signal_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    reflection_label: Mapped[str] = mapped_column(String(48), nullable=False)
    reflection_notes: Mapped[str] = mapped_column(Text, nullable=False)
    lessons_json: Mapped[list[str]] = mapped_column(
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
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class JournalEntryAttachment(Base):
    __tablename__ = "journal_entry_attachments"
    __table_args__ = (
        CheckConstraint(
            "attachment_type in ('chart_screenshot', 'signal_report', 'audit_timeline', "
            "'external_note', 'dataset_reference')",
            name="journal_entry_attachments_type_allowed",
        ),
        Index("ix_journal_entry_attachments_journal_entry_id", "journal_entry_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    journal_entry_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    attachment_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(80), nullable=False)
    reference_id: Mapped[UUID] = mapped_column(PostgresUUID(as_uuid=True), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = created_at_column()
