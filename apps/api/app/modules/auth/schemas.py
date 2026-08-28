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
    SESSION = "session"
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


class AuthSessionStatusRead(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AuthActivityEventTypeRead(StrEnum):
    REGISTER = "register"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    SESSION_REVOKE = "session_revoke"
    SESSION_REVOKE_OTHER = "session_revoke_other"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"


class AuthActivityStatusRead(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


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


class AuthRegisterRequest(ApiSchema):
    workspace_name: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)


class AuthLoginRequest(ApiSchema):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class AuthPasswordChangeRequest(ApiSchema):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=12, max_length=256)
    revoke_other_sessions: bool = True


class AuthPasswordChangeRead(ApiSchema):
    changed: bool
    revoked_session_count: int


class AuthProfileUpdateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=160)


class AuthLogoutRequest(ApiSchema):
    token: str | None = Field(default=None, min_length=1, max_length=512)


class AuthSessionCreated(ApiSchema):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    identity: CurrentIdentityRead


class AuthSessionRead(ApiReadSchema):
    id: UUID
    user_id: UUID
    workspace_id: UUID
    status: AuthSessionStatusRead
    expires_at: datetime
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
    current: bool = False


class AuthSessionBulkRevokeRead(ApiSchema):
    revoked_count: int


class AuthActivityEventRead(ApiReadSchema):
    id: UUID
    user_id: UUID | None
    workspace_id: UUID | None
    event_type: AuthActivityEventTypeRead
    status: AuthActivityStatusRead
    identity_source: str | None
    request_id: str | None
    error_code: str | None
    metadata_json: dict[str, object]
    created_at: datetime
