from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class AuthIdentityStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class AuthApiKeyStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'disabled', 'revoked')",
            name="auth_identities_status_allowed",
        ),
        UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_auth_identities_provider_subject",
        ),
        Index("ix_auth_identities_user_workspace", "user_id", "workspace_id"),
        Index("ix_auth_identities_workspace_status", "workspace_id", "status"),
    )

    id = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(320), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at = created_at_column()
    updated_at = updated_at_column()


class AuthApiKey(Base):
    __tablename__ = "auth_api_keys"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'disabled', 'revoked', 'expired')",
            name="auth_api_keys_status_allowed",
        ),
        UniqueConstraint("key_hash", name="uq_auth_api_keys_key_hash"),
        Index("ix_auth_api_keys_workspace_status", "workspace_id", "status"),
        Index("ix_auth_api_keys_prefix", "key_prefix"),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    scopes_json: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class AuthPasswordCredential(Base):
    __tablename__ = "auth_password_credentials"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'disabled', 'revoked')",
            name="auth_password_credentials_status_allowed",
        ),
        UniqueConstraint("email", name="uq_auth_password_credentials_email"),
        UniqueConstraint("user_id", name="uq_auth_password_credentials_user_id"),
        Index("ix_auth_password_credentials_workspace_status", "workspace_id", "status"),
    )

    id = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class AuthSessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'revoked', 'expired')",
            name="auth_sessions_status_allowed",
        ),
        UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        Index("ix_auth_sessions_user_status", "user_id", "status"),
        Index("ix_auth_sessions_workspace_status", "workspace_id", "status"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    id = uuid_primary_key()
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()
