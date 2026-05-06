from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from app.core.schemas import ApiReadSchema, ApiSchema
from app.modules.permissions.registry import Permission
from app.modules.users.models import UserRole


class IdentitySource(StrEnum):
    DEV = "dev"
    JWT = "jwt"
    API_KEY = "api_key"
    LEGACY_ADMIN_API_KEY = "legacy_admin_api_key"


class AuthIdentityStatusRead(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"


class AuthApiKeyStatusRead(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthUserRead(ApiSchema):
    id: UUID
    workspace_id: UUID
    email: str
    name: str
    role: UserRole


class AuthWorkspaceRead(ApiSchema):
    id: UUID
    name: str


class CurrentIdentityRead(ApiSchema):
    authenticated: bool
    source: IdentitySource | None = None
    provider: str | None = None
    provider_subject: str | None = None
    user: AuthUserRead | None = None
    workspace: AuthWorkspaceRead | None = None
    permissions: list[Permission] = Field(default_factory=list)
    scopes: list[str] = Field(default_factory=list)
    admin: bool = False


class AuthContextRead(ApiSchema):
    auth_mode: str
    auth_enabled: bool
    jwt_enabled: bool
    api_keys_enabled: bool
    api_key_header_name: str
    user_context_header_name: str
    workspace_context_header_name: str
    identity: CurrentIdentityRead


class AuthApiKeyCreate(ApiSchema):
    workspace_id: UUID | None = None
    name: str = Field(min_length=1, max_length=160)
    scopes: list[str] = Field(default_factory=list, max_length=100)
    expires_at: datetime | None = None


class AuthApiKeyCreated(ApiSchema):
    id: UUID
    workspace_id: UUID | None
    name: str
    key: str
    key_prefix: str
    status: AuthApiKeyStatusRead
    scopes: list[str]
    expires_at: datetime | None
    created_at: datetime


class AuthApiKeyRead(ApiReadSchema):
    id: UUID
    workspace_id: UUID | None
    name: str
    key_prefix: str
    status: AuthApiKeyStatusRead
    scopes: list[str]
    expires_at: datetime | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
