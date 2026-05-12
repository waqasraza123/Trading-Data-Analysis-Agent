import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import get_request_id
from app.modules.auth.identity import IdentityContext
from app.modules.auth.models import AuthActivityEvent


class AuthActivityEventType(StrEnum):
    REGISTER = "register"
    LOGIN = "login"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    SESSION_REVOKE = "session_revoke"
    SESSION_REVOKE_OTHER = "session_revoke_other"
    API_KEY_CREATE = "api_key_create"
    API_KEY_REVOKE = "api_key_revoke"


class AuthActivityStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True)
class AuthActivityContext:
    request_id: str | None = None
    client_host_hash: str | None = None
    user_agent_hash: str | None = None
    identity_source: str | None = None


@dataclass(frozen=True)
class AuthActivityDraft:
    event_type: AuthActivityEventType
    status: AuthActivityStatus
    user_id: UUID | None = None
    workspace_id: UUID | None = None
    email: str | None = None
    error_code: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class AuthActivityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        draft: AuthActivityDraft,
        context: AuthActivityContext,
        *,
        commit: bool = True,
    ) -> AuthActivityEvent:
        event = AuthActivityEvent(
            user_id=draft.user_id,
            workspace_id=draft.workspace_id,
            event_type=draft.event_type.value,
            status=draft.status.value,
            identity_source=context.identity_source,
            email_hash=hash_optional_value(draft.email),
            request_id=context.request_id,
            client_host_hash=context.client_host_hash,
            user_agent_hash=context.user_agent_hash,
            error_code=draft.error_code,
            metadata_json=bounded_metadata(draft.metadata),
        )
        self.session.add(event)
        await self.session.flush()
        if commit:
            await self.session.commit()
            await self.session.refresh(event)
        return event

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        workspace_id: UUID,
        limit: int,
    ) -> list[AuthActivityEvent]:
        result = await self.session.execute(
            select(AuthActivityEvent)
            .where(
                AuthActivityEvent.user_id == user_id,
                AuthActivityEvent.workspace_id == workspace_id,
            )
            .order_by(AuthActivityEvent.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


def activity_context_from_request(
    request: Request,
    identity: IdentityContext | None = None,
) -> AuthActivityContext:
    return AuthActivityContext(
        request_id=get_request_id(request),
        client_host_hash=hash_optional_value(request.client.host if request.client else None),
        user_agent_hash=hash_optional_value(request.headers.get("user-agent")),
        identity_source=identity.source.value if identity is not None else None,
    )


def hash_optional_value(value: str | None) -> str | None:
    normalized = value.strip().lower() if value else ""
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def bounded_metadata(metadata: dict[str, object]) -> dict[str, object]:
    clean: dict[str, object] = {}
    for key, value in metadata.items():
        if len(clean) >= 20:
            break
        if isinstance(value, str):
            clean[key] = value[:256]
        elif isinstance(value, (int, float, bool)) or value is None:
            clean[key] = value
        elif isinstance(value, list):
            clean[key] = [str(item)[:128] for item in value[:20]]
        else:
            clean[key] = str(value)[:256]
    return clean
