from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

try:
    from app.database import Base
except ImportError:
    try:
        from app.db import Base
    except ImportError:
        try:
            from app.core.database import Base
        except ImportError:
            from sqlalchemy.orm import DeclarativeBase

            class Base(DeclarativeBase):
                pass


class SafetyPolicySet(Base):
    __tablename__ = "safety_policy_sets"
    __table_args__ = (
        Index("ix_safety_policy_sets_key_version_status", "key", "version", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SafetyPolicyEvaluation(Base):
    __tablename__ = "safety_policy_evaluations"
    __table_args__ = (
        Index("ix_safety_policy_evaluations_workspace_created_at", "workspace_id", "created_at"),
        Index("ix_safety_policy_evaluations_source_type_source_id", "source_type", "source_id"),
        Index("ix_safety_policy_evaluations_safety_status", "safety_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    policy_set_key: Mapped[str] = mapped_column(String(120), nullable=False)
    policy_set_version: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    evaluation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    safety_status: Mapped[str] = mapped_column(String(40), nullable=False)
    input_summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    findings_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    redacted_output_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(
        JSONB, nullable=True
    )
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
