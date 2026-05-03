from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class StateMachineDefinitionStatus(StrEnum):
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class StateTransitionValidationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"


class StateMachineDefinition(Base):
    __tablename__ = "state_machine_definitions"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'draft', 'archived')",
            name="state_machine_definitions_status_allowed",
        ),
        UniqueConstraint("key", "version", name="uq_state_machine_definitions_key_version"),
        Index("ix_state_machine_definitions_key", "key"),
        Index("ix_state_machine_definitions_object_type", "object_type"),
        Index("ix_state_machine_definitions_status", "status"),
    )

    id = uuid_primary_key()
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    object_type: Mapped[str] = mapped_column(String(120), nullable=False)
    states_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    transitions_json: Mapped[list[dict[str, object]]] = mapped_column(JSONB, nullable=False)
    terminal_states_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at = created_at_column()
    updated_at = updated_at_column()


class StateTransitionValidation(Base):
    __tablename__ = "state_transition_validations"
    __table_args__ = (
        CheckConstraint(
            "validation_status in ('valid', 'invalid')",
            name="state_transition_validations_status_allowed",
        ),
        Index("ix_state_transition_validations_workspace_created", "workspace_id", "created_at"),
        Index("ix_state_transition_validations_machine", "state_machine_key", "state_machine_version"),
        Index("ix_state_transition_validations_object", "object_type", "object_id"),
        Index("ix_state_transition_validations_status", "validation_status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    state_machine_key: Mapped[str] = mapped_column(String(120), nullable=False)
    state_machine_version: Mapped[str] = mapped_column(String(40), nullable=False)
    object_type: Mapped[str] = mapped_column(String(120), nullable=False)
    object_id: Mapped[UUID | None] = mapped_column(PostgresUUID(as_uuid=True), nullable=True)
    from_state: Mapped[str] = mapped_column(String(80), nullable=False)
    to_state: Mapped[str] = mapped_column(String(80), nullable=False)
    validation_status: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = created_at_column()
