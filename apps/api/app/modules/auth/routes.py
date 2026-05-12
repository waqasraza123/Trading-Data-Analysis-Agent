from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.dependencies import database_session
from app.modules.auth.api_keys import ApiKeyService
from app.modules.auth.dependencies import optional_identity, require_admin
from app.modules.auth.identity import IdentityContext, identity_to_read
from app.modules.auth.models import AuthApiKey, AuthSession
from app.modules.auth.passwords import PasswordAuthService, hash_session_token
from app.modules.auth.schemas import (
    AuthApiKeyCreate,
    AuthApiKeyCreated,
    AuthApiKeyRead,
    AuthApiKeyStatusRead,
    AuthContextRead,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthPasswordChangeRead,
    AuthPasswordChangeRequest,
    AuthRegisterRequest,
    AuthSessionCreated,
    AuthSessionBulkRevokeRead,
    AuthSessionRead,
    AuthSessionStatusRead,
    CurrentIdentityRead,
    IdentitySource,
)
from app.modules.auth.settings import auth_is_enforced, effective_auth_mode
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthSessionCreated, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegisterRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthSessionCreated:
    created_session = await PasswordAuthService(
        session=session,
        settings=request.app.state.settings,
    ).register(
        workspace_name=payload.workspace_name,
        name=payload.name,
        email=payload.email,
        password=payload.password,
    )
    return AuthSessionCreated(
        access_token=created_session.token,
        expires_at=created_session.expires_at,
        identity=identity_to_read(created_session.identity),
    )


@router.post("/login", response_model=AuthSessionCreated)
async def login(
    payload: AuthLoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthSessionCreated:
    created_session = await PasswordAuthService(
        session=session,
        settings=request.app.state.settings,
    ).login(email=payload.email, password=payload.password)
    return AuthSessionCreated(
        access_token=created_session.token,
        expires_at=created_session.expires_at,
        identity=identity_to_read(created_session.identity),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: AuthLogoutRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> None:
    token = payload.token or bearer_token(request)
    if token is not None:
        await PasswordAuthService(
            session=session,
            settings=request.app.state.settings,
        ).revoke_session(token)


@router.get("/sessions", response_model=list[AuthSessionRead])
async def list_sessions(
    request: Request,
    identity: Annotated[IdentityContext, Depends(require_session_user_identity)],
    session: Annotated[AsyncSession, Depends(database_session)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AuthSessionRead]:
    user = session_identity_user(identity)
    service = PasswordAuthService(session=session, settings=request.app.state.settings)
    sessions = await service.list_user_sessions(
        user_id=user.id,
        workspace_id=user.workspace_id,
        limit=limit,
    )
    current_token_hash = current_session_token_hash(request)
    return [session_to_read(auth_session, current_token_hash) for auth_session in sessions]


@router.post("/sessions/revoke-other", response_model=AuthSessionBulkRevokeRead)
async def revoke_other_sessions(
    request: Request,
    identity: Annotated[IdentityContext, Depends(require_session_user_identity)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthSessionBulkRevokeRead:
    user = session_identity_user(identity)
    revoked_count = await PasswordAuthService(
        session=session,
        settings=request.app.state.settings,
    ).revoke_other_user_sessions(
        user_id=user.id,
        workspace_id=user.workspace_id,
        current_token=bearer_token(request),
    )
    return AuthSessionBulkRevokeRead(revoked_count=revoked_count)


@router.post("/sessions/{session_id}/revoke", response_model=AuthSessionRead)
async def revoke_session_by_id(
    session_id: UUID,
    request: Request,
    identity: Annotated[IdentityContext, Depends(require_session_user_identity)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthSessionRead:
    user = session_identity_user(identity)
    auth_session = await PasswordAuthService(
        session=session,
        settings=request.app.state.settings,
    ).revoke_user_session(
        session_id=session_id,
        user_id=user.id,
        workspace_id=user.workspace_id,
    )
    return session_to_read(auth_session, current_session_token_hash(request))


@router.post("/password/change", response_model=AuthPasswordChangeRead)
async def change_password(
    payload: AuthPasswordChangeRequest,
    request: Request,
    identity: Annotated[IdentityContext, Depends(require_session_user_identity)],
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthPasswordChangeRead:
    user = session_identity_user(identity)
    revoked_count = await PasswordAuthService(
        session=session,
        settings=request.app.state.settings,
    ).change_password(
        user_id=user.id,
        workspace_id=user.workspace_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
        revoke_other_sessions=payload.revoke_other_sessions,
        current_token=bearer_token(request),
    )
    return AuthPasswordChangeRead(changed=True, revoked_session_count=revoked_count)


@router.get("/me", response_model=CurrentIdentityRead)
async def get_auth_me(
    request: Request,
    identity: Annotated[IdentityContext | None, Depends(optional_identity)],
) -> CurrentIdentityRead:
    if identity is None and auth_is_enforced(request.app.state.settings):
        raise AppError(401, "authentication_required", "Authentication is required")
    return identity_to_read(identity)


@router.get("/context", response_model=AuthContextRead)
async def get_auth_context(
    request: Request,
    identity: Annotated[IdentityContext | None, Depends(optional_identity)],
) -> AuthContextRead:
    settings = request.app.state.settings
    return AuthContextRead(
        auth_mode=effective_auth_mode(settings).value,
        auth_enabled=settings.auth_enabled,
        jwt_enabled=settings.auth_jwt_enabled,
        api_keys_enabled=settings.auth_api_keys_enabled,
        api_key_header_name=settings.api_key_header_name,
        user_context_header_name=settings.user_context_header_name,
        workspace_context_header_name=settings.workspace_context_header_name,
        identity=identity_to_read(identity),
    )


@router.post(
    "/api-keys",
    response_model=AuthApiKeyCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin())],
)
async def create_api_key(
    payload: AuthApiKeyCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthApiKeyCreated:
    service = ApiKeyService(session=session, settings=request.app.state.settings)
    api_key, raw_key = await service.create(
        name=payload.name,
        workspace_id=payload.workspace_id,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )
    return AuthApiKeyCreated(
        id=api_key.id,
        workspace_id=api_key.workspace_id,
        name=api_key.name,
        key=raw_key,
        key_prefix=api_key.key_prefix,
        status=AuthApiKeyStatusRead(api_key.status),
        scopes=api_key.scopes_json,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get(
    "/api-keys",
    response_model=list[AuthApiKeyRead],
    dependencies=[Depends(require_admin())],
)
async def list_api_keys(
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
    workspace_id: Annotated[UUID | None, Query(alias="workspaceId")] = None,
) -> list[AuthApiKeyRead]:
    api_keys = await ApiKeyService(session=session, settings=request.app.state.settings).list(
        workspace_id=workspace_id
    )
    return [api_key_to_read(api_key) for api_key in api_keys]


@router.post(
    "/api-keys/{key_id}/revoke",
    response_model=AuthApiKeyRead,
    dependencies=[Depends(require_admin())],
)
async def revoke_api_key(
    key_id: UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(database_session)],
) -> AuthApiKeyRead:
    service = ApiKeyService(session=session, settings=request.app.state.settings)
    api_key = await service.revoke(key_id)
    return api_key_to_read(api_key)


def api_key_to_read(api_key: AuthApiKey) -> AuthApiKeyRead:
    return AuthApiKeyRead(
        id=api_key.id,
        workspace_id=api_key.workspace_id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        status=AuthApiKeyStatusRead(api_key.status),
        scopes=api_key.scopes_json,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
    )


def session_to_read(
    auth_session: AuthSession,
    current_token_hash: str | None,
) -> AuthSessionRead:
    return AuthSessionRead(
        id=auth_session.id,
        user_id=auth_session.user_id,
        workspace_id=auth_session.workspace_id,
        status=AuthSessionStatusRead(auth_session.status),
        expires_at=auth_session.expires_at,
        last_seen_at=auth_session.last_seen_at,
        created_at=auth_session.created_at,
        updated_at=auth_session.updated_at,
        current=current_token_hash is not None and auth_session.token_hash == current_token_hash,
    )


async def require_session_user_identity(
    identity: Annotated[IdentityContext | None, Depends(optional_identity)],
) -> IdentityContext:
    if identity is None or identity.user is None or identity.source != IdentitySource.SESSION:
        raise AppError(401, "session_auth_required", "Session authentication is required")
    return identity


def session_identity_user(identity: IdentityContext) -> User:
    if identity.user is None:
        raise AppError(401, "session_auth_required", "Session authentication is required")
    return identity.user


def current_session_token_hash(request: Request) -> str | None:
    token = bearer_token(request)
    return hash_session_token(token) if token is not None else None


def bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if authorization is None or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip() or None
