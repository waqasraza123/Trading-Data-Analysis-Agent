from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.columns import created_at_column, updated_at_column, uuid_primary_key


class ProviderCredentialType(StrEnum):
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH = "oauth"
    WEBHOOK_SECRET = "webhook_secret"
    ADC = "adc"
    NONE_REQUIRED = "none_required"


class ProviderCredentialStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    REVOKED = "revoked"
    MISSING = "missing"
    TEST_FAILED = "test_failed"


class ProviderConnectionTestType(StrEnum):
    CONFIGURATION_ONLY = "configuration_only"
    MOCK = "mock"
    PUBLIC_ENDPOINT = "public_endpoint"
    AUTHENTICATED_ENDPOINT = "authenticated_endpoint"


class ProviderConnectionTestStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PROVIDER_NOT_CONFIGURED = "provider_not_configured"


class ProviderCredentialRef(Base):
    __tablename__ = "provider_credential_refs"
    __table_args__ = (
        CheckConstraint(
            "credential_type in ('api_key', 'bearer_token', 'basic_auth', 'oauth', "
            "'webhook_secret', 'adc', 'none_required')",
            name="provider_credential_refs_credential_type_allowed",
        ),
        CheckConstraint(
            "status in ('active', 'paused', 'revoked', 'missing', 'test_failed')",
            name="provider_credential_refs_status_allowed",
        ),
        CheckConstraint(
            "last_test_status is null or last_test_status in "
            "('passed', 'failed', 'skipped', 'provider_not_configured')",
            name="provider_credential_refs_last_test_status_allowed",
        ),
        Index(
            "ix_provider_credential_refs_workspace_provider_status",
            "workspace_id",
            "provider",
            "status",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    last_test_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = created_at_column()
    updated_at = updated_at_column()


class ProviderConnectionTest(Base):
    __tablename__ = "provider_connection_tests"
    __table_args__ = (
        CheckConstraint(
            "test_type in ('configuration_only', 'mock', 'public_endpoint', "
            "'authenticated_endpoint')",
            name="provider_connection_tests_test_type_allowed",
        ),
        CheckConstraint(
            "status in ('passed', 'failed', 'skipped', 'provider_not_configured')",
            name="provider_connection_tests_status_allowed",
        ),
        Index(
            "ix_provider_connection_tests_credential_created",
            "credential_ref_id",
            "created_at",
        ),
        Index(
            "ix_provider_connection_tests_workspace_provider_status",
            "workspace_id",
            "provider",
            "status",
        ),
    )

    id = uuid_primary_key()
    workspace_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    credential_ref_id: Mapped[UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("provider_credential_refs.id", ondelete="SET NULL"),
        nullable=True,
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    test_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    response_metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_at_column()
