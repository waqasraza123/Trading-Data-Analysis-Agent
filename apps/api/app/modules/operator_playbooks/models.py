from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class OperatorPlaybookEvaluationStatus(StrEnum):
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"


class OperatorPlaybookRecommendationType(StrEnum):
    REVIEW_DATA_QUALITY = "review_data_quality"
    REVIEW_PROFILE_SIMULATION = "review_profile_simulation"
    REVIEW_DECISION_READINESS = "review_decision_readiness"
    REVIEW_MARKET_SESSION = "review_market_session"
    NO_ACTION = "no_action"


class OperatorPlaybook(Base):
    __tablename__ = "operator_playbooks"
    __table_args__ = (
        CheckConstraint("priority >= 0", name="operator_playbooks_priority_non_negative"),
        Index("uq_operator_playbooks_key_version", "key", "version", unique=True),
        Index("ix_operator_playbooks_enabled", "is_enabled"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rules_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
    updated_at = updated_at_column()


class OperatorPlaybookEvaluation(Base):
    __tablename__ = "operator_playbook_evaluations"
    __table_args__ = (
        CheckConstraint(
            "status in ('completed', 'completed_with_warnings', 'failed')",
            name="operator_playbook_evaluations_status_allowed",
        ),
        CheckConstraint(
            "recommendation_type in ('review_data_quality', 'review_profile_simulation', "
            "'review_decision_readiness', 'review_market_session', 'no_action')",
            name="operator_playbook_evaluations_recommendation_allowed",
        ),
        Index("ix_operator_playbook_evaluations_workspace_created", "workspace_id", "created_at"),
        Index("ix_operator_playbook_evaluations_playbook_id", "playbook_id"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    playbook_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("operator_playbooks.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(48), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(48), nullable=False)
    subject_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    result_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at = created_at_column()
