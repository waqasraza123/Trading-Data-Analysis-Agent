from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.dependencies import database_session
from app.modules.auth.api_keys import ApiKeyService
from app.modules.auth.dependencies import optional_identity, require_admin
from app.modules.auth.identity import IdentityContext, identity_to_read
from app.modules.auth.models import AuthApiKey
from app.modules.auth.schemas import (
    AuthApiKeyCreate,
    AuthApiKeyCreated,
    AuthApiKeyRead,
    AuthApiKeyStatusRead,
    AuthContextRead,
    CurrentIdentityRead,
)
from app.modules.auth.settings import auth_is_enforced, effective_auth_mode

router = APIRouter(prefix="/auth", tags=["auth"])


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
