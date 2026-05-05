from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.provider_credentials.models import (
    ProviderConnectionTestStatus,
    ProviderConnectionTestType,
    ProviderCredentialStatus,
    ProviderCredentialType,
)


class ProviderCredentialRefCreate(ApiSchema):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=160)
    provider: str = Field(min_length=1, max_length=64)
    credential_type: ProviderCredentialType
    status: ProviderCredentialStatus = ProviderCredentialStatus.ACTIVE
    secret_ref: str | None = Field(default=None, min_length=1, max_length=255)
    public_metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "provider", "secret_ref")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized.lower() if normalized and value == value.lower() else normalized

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()


class ProviderCredentialRefUpdate(ApiSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    credential_type: ProviderCredentialType | None = None
    status: ProviderCredentialStatus | None = None
    secret_ref: str | None = Field(default=None, min_length=1, max_length=255)
    public_metadata_json: dict[str, Any] | None = None

    @field_validator("name", "secret_ref")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()


class ProviderCredentialRefRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    name: str
    provider: str
    credential_type: ProviderCredentialType
    status: ProviderCredentialStatus
    secret_ref_configured: bool
    secret_ref_summary: dict[str, Any] | None
    public_metadata_json: dict[str, Any]
    last_test_status: ProviderConnectionTestStatus | None
    last_tested_at: datetime | None
    last_error_message: str | None
    rotated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ProviderConnectionTestRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID
    credential_ref_id: UUID | None
    provider: str
    test_type: ProviderConnectionTestType
    status: ProviderConnectionTestStatus
    request_metadata_json: dict[str, Any]
    response_metadata_json: dict[str, Any]
    error_message: str | None
    created_at: datetime


class ProviderCredentialTestRequest(ApiSchema):
    test_type: ProviderConnectionTestType | None = None


class ProviderConfigurationTestRequest(ApiSchema):
    workspace_id: UUID
    provider: str = Field(min_length=1, max_length=64)
    credential_type: ProviderCredentialType = ProviderCredentialType.NONE_REQUIRED
    test_type: ProviderConnectionTestType = ProviderConnectionTestType.CONFIGURATION_ONLY
    request_metadata_json: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_test_type(self) -> "ProviderConfigurationTestRequest":
        if self.test_type == ProviderConnectionTestType.AUTHENTICATED_ENDPOINT:
            return self
        return self


class ProviderCredentialListFilters(ApiSchema):
    workspace_id: UUID | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    status: ProviderCredentialStatus | None = None
    credential_type: ProviderCredentialType | None = None
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)

    @field_validator("provider")
    @classmethod
    def normalize_provider(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().lower()
