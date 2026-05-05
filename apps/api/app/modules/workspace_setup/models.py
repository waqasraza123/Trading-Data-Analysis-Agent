from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class WorkspaceSetupRun(Base):
    __tablename__ = "workspace_setup_runs"
    __table_args__ = (
        CheckConstraint(
            "status in ('draft', 'running', 'completed', 'completed_with_warnings', "
            "'failed', 'cancelled')",
            name="workspace_setup_runs_status_allowed",
        ),
        Index("ix_workspace_setup_runs_workspace_status", "workspace_id", "status"),
        Index("ix_workspace_setup_runs_user_status", "user_id", "status"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    setup_version: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_steps_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    skipped_steps_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    failed_steps_json: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )
    result_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkspaceSetupStepResult(Base):
    __tablename__ = "workspace_setup_step_results"
    __table_args__ = (
        CheckConstraint(
            "step_key in ('workspace', 'user', 'symbols', 'data_source', "
            "'credential_reference', 'watchlist', 'scanner_preset', 'preference_profile', "
            "'demo_data', 'readiness_check', 'first_scan')",
            name="workspace_setup_step_results_step_key_allowed",
        ),
        CheckConstraint(
            "status in ('pending', 'completed', 'skipped', 'failed')",
            name="workspace_setup_step_results_status_allowed",
        ),
        Index(
            "ix_workspace_setup_step_results_run_step",
            "setup_run_id",
            "step_key",
            unique=True,
        ),
    )

    id = uuid_primary_key()
    setup_run_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspace_setup_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    step_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    output_json: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
