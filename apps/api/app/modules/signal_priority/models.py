from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class SignalPriorityLabel(StrEnum):
    URGENT_REVIEW = "urgent_review"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    AVOID = "avoid"
    STALE = "stale"


class SignalReviewBucket(StrEnum):
    HIGH_QUALITY_CONTEXT = "high_quality_context"
    NEEDS_CONFIRMATION = "needs_confirmation"
    CONFLICTED = "conflicted"
    AVOID_OR_NO_DIRECTIONAL_SIGNAL = "avoid_or_no_directional_signal"
    STALE_OR_DATA_ISSUE = "stale_or_data_issue"
    REVIEW_REQUIRED = "review_required"


class SignalPriorityScore(Base):
    __tablename__ = "signal_priority_scores"
    __table_args__ = (
        CheckConstraint(
            "priority_score >= 0 and priority_score <= 1",
            name="signal_priority_score_range",
        ),
        CheckConstraint(
            "priority_label in ('urgent_review', 'high', 'medium', 'low', 'avoid', 'stale')",
            name="signal_priority_label_allowed",
        ),
        CheckConstraint(
            "review_bucket in ('high_quality_context', 'needs_confirmation', 'conflicted', "
            "'avoid_or_no_directional_signal', 'stale_or_data_issue', 'review_required')",
            name="signal_priority_review_bucket_allowed",
        ),
        UniqueConstraint("signal_id", "priority_version", name="uq_signal_priority_signal_version"),
        Index("ix_signal_priority_workspace_label", "workspace_id", "priority_label"),
        Index("ix_signal_priority_workspace_bucket", "workspace_id", "review_bucket"),
        Index(
            "ix_signal_priority_workspace_symbol_timeframe",
            "workspace_id",
            "symbol_id",
            "timeframe",
        ),
        Index("ix_signal_priority_signal_id", "signal_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
    )
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False)
    priority_version: Mapped[str] = mapped_column(String(32), nullable=False)
    priority_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    priority_label: Mapped[str] = mapped_column(String(32), nullable=False)
    review_bucket: Mapped[str] = mapped_column(String(48), nullable=False)
    component_scores_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    penalties_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    boosters_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    reasons_json: Mapped[list[dict[str, object]]] = mapped_column(
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
