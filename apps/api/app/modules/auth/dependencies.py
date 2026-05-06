import logging
from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, get_request_id
from app.db.session import get_database_session
from app.modules.auth.api_keys import (
    LEGACY_ADMIN_API_KEY_HEADER_NAME,
    ApiKeyService,
    legacy_admin_key_is_valid,
)
from app.modules.auth.identity import (
    IdentityContext,
    build_api_key_identity,
    build_dev_identity,
    build_jwt_identity,
)
from app.modules.auth.jwt import JwtVerifier
from app.modules.auth.settings import AuthMode, auth_is_enforced, effective_auth_mode
from app.modules.auth.workspace_context import resolve_request_workspace_id
from app.modules.permissions.registry import Permission
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace


async def optional_identity(
    request: Request,
) -> IdentityContext | None:
    if not auth_is_enforced(request.app.state.settings) and not request_has_auth_candidate(request):
        return None
    return await resolve_identity_from_database(request=request, required=False)


async def get_current_identity(
    request: Request,
) -> IdentityContext:
    identity = await resolve_identity_from_database(request=request, required=True)
    if identity is None:
        raise AppError(401, "authentication_required", "Authentication is required")
    return identity


async def get_current_user(
    identity: Annotated[IdentityContext, Depends(get_current_identity)],
) -> User:
    if identity.user is None:
        raise AppError(401, "user_context_required", "User context is required")
    return identity.user


async def get_current_workspace(
    identity: Annotated[IdentityContext, Depends(get_current_identity)],
) -> Workspace:
    if identity.workspace is None:
        raise AppError(401, "workspace_context_required", "Workspace context is required")
    return identity.workspace


def require_workspace_member() -> Callable[[Request, IdentityContext], Awaitable[None]]:
    async def dependency(
        request: Request,
        identity: Annotated[IdentityContext, Depends(get_current_identity)],
    ) -> None:
        workspace_id = await resolve_request_workspace_id(request)
        if identity.can_access_workspace(workspace_id):
            return
        log_auth_failure(
            request=request,
            permission=Permission.WORKSPACE_READ,
            workspace_id=workspace_id,
            identity=identity,
            reason="workspace_mismatch",
        )
        raise AppError(403, "workspace_access_denied", "Workspace access denied")

    return dependency


def require_permission(
    permission: Permission,
) -> Callable[[Request], Awaitable[None]]:
    async def dependency(
        request: Request,
    ) -> None:
        settings = request.app.state.settings
        if not auth_is_enforced(settings):
            return
        if legacy_admin_header_is_valid(request):
            return
        if not request_has_auth_candidate(request):
            raise AppError(401, "authentication_required", "Authentication is required")
        identity = await resolve_identity_from_database(request=request, required=True)
        if identity is None:
            raise AppError(401, "authentication_required", "Authentication is required")
        workspace_id = await resolve_request_workspace_id(request)
        if identity.has_permission(permission, workspace_id):
            return
        log_auth_failure(
            request=request,
            permission=permission,
            workspace_id=workspace_id,
            identity=identity,
            reason="missing_permission",
        )
        raise AppError(403, "permission_denied", "Permission denied")

    return dependency


def require_admin() -> Callable[[Request], Awaitable[None]]:
    async def dependency(
        request: Request,
    ) -> None:
        settings = request.app.state.settings
        if not auth_is_enforced(settings):
            return
        if legacy_admin_header_is_valid(request):
            return
        if not request_has_auth_candidate(request):
            raise AppError(401, "authentication_required", "Authentication is required")
        identity = await resolve_identity_from_database(request=request, required=True)
        if identity is not None and identity.admin:
            return
        log_auth_failure(
            request=request,
            permission=None,
            workspace_id=None,
            identity=identity,
            reason="admin_required",
        )
        raise AppError(403, "permission_denied", "Permission denied")

    return dependency


async def resolve_identity_from_database(
    *,
    request: Request,
    required: bool,
) -> IdentityContext | None:
    async for session in get_database_session():
        return await resolve_identity(request=request, session=session, required=required)
    if required:
        raise AppError(500, "database_session_unavailable", "Database session is unavailable")
    return None


async def resolve_identity(
    *,
    request: Request,
    session: AsyncSession,
    required: bool,
) -> IdentityContext | None:
    cached = getattr(request.state, "auth_identity", None)
    if isinstance(cached, IdentityContext):
        return cached
    settings = request.app.state.settings
    mode = effective_auth_mode(settings)
    identity: IdentityContext | None
    if mode == AuthMode.DEV:
        identity = await build_dev_identity(
            settings=settings,
            session=session,
            user_id_header=request.headers.get(settings.user_context_header_name),
            workspace_id_header=request.headers.get(settings.workspace_context_header_name),
        )
        request.state.auth_identity = identity
        if identity is None and required and settings.auth_enabled:
            raise AppError(401, "authentication_required", "Authentication is required")
        return identity
    if mode == AuthMode.JWT:
        identity = await resolve_jwt_identity(request=request, session=session, required=required)
    elif mode == AuthMode.API_KEY:
        identity = await resolve_api_key_identity(
            request=request,
            session=session,
            required=required,
        )
    else:
        identity = await resolve_jwt_identity(request=request, session=session, required=False)
        if identity is None:
            identity = await resolve_api_key_identity(
                request=request,
                session=session,
                required=required,
            )
    request.state.auth_identity = identity
    return identity


async def resolve_api_key_identity(
    *,
    request: Request,
    session: AsyncSession,
    required: bool,
) -> IdentityContext | None:
    settings = request.app.state.settings
    if not settings.auth_api_keys_enabled:
        if required:
            raise AppError(401, "api_key_disabled", "API-key authentication is disabled")
        return None
    raw_key = request.headers.get(settings.api_key_header_name) or request.headers.get(
        LEGACY_ADMIN_API_KEY_HEADER_NAME
    )
    if raw_key is None:
        if required:
            raise AppError(401, "authentication_required", "Authentication is required")
        return None
    validation = await ApiKeyService(session=session, settings=settings).validate(raw_key)
    if not validation.valid:
        if required:
            raise AppError(401, "invalid_credentials", "Credentials are invalid")
        return None
    return await build_api_key_identity(
        session=session,
        validation_api_key=validation.api_key,
        legacy_admin=validation.legacy_admin,
    )


async def resolve_jwt_identity(
    *,
    request: Request,
    session: AsyncSession,
    required: bool,
) -> IdentityContext | None:
    settings = request.app.state.settings
    authorization = request.headers.get("authorization")
    if authorization is None or not authorization.lower().startswith("bearer "):
        if required:
            raise AppError(401, "authentication_required", "Authentication is required")
        return None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        if required:
            raise AppError(401, "invalid_token", "Token is invalid")
        return None
    claims = JwtVerifier(settings).verify(token)
    return await build_jwt_identity(session=session, claims=claims, settings=settings)


def log_auth_failure(
    *,
    request: Request,
    permission: Permission | None,
    workspace_id: UUID | None,
    identity: IdentityContext | None,
    reason: str,
) -> None:
    request.state.error_code = "permission_denied"
    logger = logging.getLogger(request.app.state.settings.service_name)
    logger.warning(
        "permission_denied",
        extra={
            "request_id": get_request_id(request),
            "path": request.url.path,
            "method": request.method,
            "permission": permission.value if permission is not None else None,
            "workspace_id": str(workspace_id) if workspace_id is not None else None,
            "identity_source": identity.source.value if identity is not None else None,
            "user_id": str(identity.user.id) if identity is not None and identity.user else None,
            "reason": reason,
        },
    )


def legacy_admin_header_is_valid(request: Request) -> bool:
    settings = request.app.state.settings
    supplied_key = request.headers.get(settings.api_key_header_name) or request.headers.get(
        LEGACY_ADMIN_API_KEY_HEADER_NAME,
        "",
    )
    return legacy_admin_key_is_valid(supplied_key, settings)


def request_has_auth_candidate(request: Request) -> bool:
    settings = request.app.state.settings
    return any(
        (
            bool(request.headers.get("authorization")),
            bool(request.headers.get(settings.api_key_header_name)),
            bool(request.headers.get(LEGACY_ADMIN_API_KEY_HEADER_NAME)),
            bool(request.headers.get(settings.user_context_header_name)),
            bool(request.headers.get(settings.workspace_context_header_name)),
        )
    )
