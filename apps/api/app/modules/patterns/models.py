from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, uuid_primary_key


class PatternCandidate(Base):
    __tablename__ = "pattern_candidates"
    __table_args__ = (
        CheckConstraint(
            "bias in ('bullish', 'bearish', 'neutral')",
            name="pattern_candidate_bias_allowed",
        ),
        CheckConstraint(
            "strength_score >= 0 and strength_score <= 1",
            name="pattern_candidate_strength_score_range",
        ),
        Index("ix_pattern_candidates_analysis_run_id", "analysis_run_id"),
        Index(
            "ix_pattern_candidates_workspace_symbol_type",
            "workspace_id",
            "symbol_id",
            "pattern_type",
        ),
        Index("ix_pattern_candidates_selected", "analysis_run_id", "is_selected"),
    )

    id = uuid_primary_key()
    analysis_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    symbol_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("symbols.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    bias: Mapped[str] = mapped_column(String(16), nullable=False)
    strength_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    is_selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    evidence_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    risk_notes_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    metrics_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
