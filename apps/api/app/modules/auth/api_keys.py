import hashlib
import secrets
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.modules.auth.models import AuthApiKey, AuthApiKeyStatus

LEGACY_ADMIN_API_KEY_HEADER_NAME = "x-admin-api-key"
API_KEY_PREFIX_LENGTH = 16


class ApiKeyValidationResult:
    def __init__(
        self,
        *,
        valid: bool,
        api_key: AuthApiKey | None = None,
        legacy_admin: bool = False,
    ) -> None:
        self.valid = valid
        self.api_key = api_key
        self.legacy_admin = legacy_admin


class ApiKeyService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def validate(self, raw_key: str) -> ApiKeyValidationResult:
        if not raw_key.strip():
            return ApiKeyValidationResult(valid=False)
        if legacy_admin_key_is_valid(raw_key, self.settings):
            return ApiKeyValidationResult(valid=True, legacy_admin=True)
        key_hash = hash_api_key(raw_key)
        statement = select(AuthApiKey).where(AuthApiKey.key_hash == key_hash)
        result = await self.session.execute(statement)
        api_key = result.scalar_one_or_none()
        if api_key is None:
            return ApiKeyValidationResult(valid=False)
        now = datetime.now(UTC)
        if api_key.expires_at is not None and api_key.expires_at < now:
            api_key.status = AuthApiKeyStatus.EXPIRED.value
            await self.session.flush()
            return ApiKeyValidationResult(valid=False, api_key=api_key)
        if api_key.status != AuthApiKeyStatus.ACTIVE.value:
            return ApiKeyValidationResult(valid=False, api_key=api_key)
        api_key.last_used_at = now
        await self.session.flush()
        return ApiKeyValidationResult(valid=True, api_key=api_key)

    async def create(
        self,
        *,
        name: str,
        workspace_id: UUID | None,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> tuple[AuthApiKey, str]:
        raw_key = generate_api_key()
        api_key = AuthApiKey(
            workspace_id=workspace_id,
            name=name.strip(),
            key_hash=hash_api_key(raw_key),
            key_prefix=api_key_prefix(raw_key),
            status=AuthApiKeyStatus.ACTIVE.value,
            scopes_json=normalize_scopes(scopes),
            expires_at=expires_at,
        )
        self.session.add(api_key)
        await self.session.flush()
        await self.session.refresh(api_key)
        return api_key, raw_key

    async def list(self, workspace_id: UUID | None = None) -> list[AuthApiKey]:
        statement = select(AuthApiKey).order_by(AuthApiKey.created_at.desc())
        if workspace_id is not None:
            statement = statement.where(AuthApiKey.workspace_id == workspace_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def revoke(self, key_id: UUID) -> AuthApiKey:
        api_key = await self.session.get(AuthApiKey, key_id)
        if api_key is None:
            from app.core.errors import AppError

            raise AppError(404, "api_key_not_found", "API key not found")
        api_key.status = AuthApiKeyStatus.REVOKED.value
        await self.session.flush()
        await self.session.refresh(api_key)
        return api_key


def generate_api_key() -> str:
    return f"tai_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def api_key_prefix(raw_key: str) -> str:
    return raw_key[:API_KEY_PREFIX_LENGTH]


def normalize_scopes(scopes: list[str]) -> list[str]:
    normalized: list[str] = []
    for scope in scopes:
        item = scope.strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def legacy_admin_key_is_valid(raw_key: str, settings: Settings) -> bool:
    if settings.admin_api_key is None:
        return False
    return secrets.compare_digest(raw_key, settings.admin_api_key.get_secret_value())
