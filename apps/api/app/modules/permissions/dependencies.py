import logging
import secrets
from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.core.errors import AppError, get_request_id
from app.db.session import get_database_session
from app.modules.permissions.registry import Permission
from app.modules.permissions.service import user_has_permission
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository

CURRENT_USER_ID_HEADER = "x-user-id"


async def resolve_current_user_optional(
    request: Request,
) -> User | None:
    user_id_header = request.headers.get(CURRENT_USER_ID_HEADER)
    if user_id_header is None or not user_id_header.strip():
        return None
    try:
        user_id = UUID(user_id_header.strip())
    except ValueError as error:
        raise AppError(401, "invalid_user_context", "User context is invalid") from error
    async for session in get_database_session():
        user = await UserRepository(session).get_by_id(user_id)
        if user is None:
            raise AppError(401, "invalid_user_context", "User context is invalid")
        return user
    raise AppError(500, "database_session_unavailable", "Database session is unavailable")


def enforce_if_auth_enabled(
    request: Request,
    user: User | None,
) -> bool:
    if not request.app.state.settings.auth_enabled:
        return False
    if user is not None:
        return True
    if admin_api_key_is_valid(request):
        return True
    log_permission_failure(
        request=request,
        permission=None,
        workspace_id=None,
        user=user,
        reason="missing_user_or_api_key",
    )
    raise AppError(401, "authentication_required", "Authentication is required")


def require_permission(
    permission: Permission,
) -> Callable[[Request, User | None], Awaitable[None]]:
    async def dependency(
        request: Request,
        user: Annotated[User | None, Depends(resolve_current_user_optional)] = None,
    ) -> None:
        if not request.app.state.settings.auth_enabled:
            return
        if admin_api_key_is_valid(request):
            return
        enforce_if_auth_enabled(request=request, user=user)
        if user_has_permission(user=user, permission=permission):
            return
        log_permission_failure(
            request=request,
            permission=permission,
            workspace_id=None,
            user=user,
            reason="missing_permission",
        )
        raise AppError(403, "permission_denied", "Permission denied")

    return dependency


def require_workspace_access(
    workspace_id: UUID,
) -> Callable[[Request, User | None], Awaitable[None]]:
    async def dependency(
        request: Request,
        user: Annotated[User | None, Depends(resolve_current_user_optional)] = None,
    ) -> None:
        if not request.app.state.settings.auth_enabled:
            return
        if admin_api_key_is_valid(request):
            return
        enforce_if_auth_enabled(request=request, user=user)
        if user is not None and user.workspace_id == workspace_id:
            return
        log_permission_failure(
            request=request,
            permission=Permission.WORKSPACE_READ,
            workspace_id=workspace_id,
            user=user,
            reason="workspace_mismatch",
        )
        raise AppError(403, "workspace_access_denied", "Workspace access denied")

    return dependency


def admin_api_key_is_valid(request: Request) -> bool:
    settings = request.app.state.settings
    if not settings.auth_enabled or settings.admin_api_key is None:
        return False
    supplied_key = request.headers.get(settings.api_key_header_name, "")
    return secrets.compare_digest(supplied_key, settings.admin_api_key.get_secret_value())


def log_permission_failure(
    request: Request,
    permission: Permission | None,
    workspace_id: UUID | None,
    user: User | None,
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
            "user_id": str(user.id) if user is not None else None,
            "user_role": str(UserRole(user.role).value) if user is not None else None,
            "reason": reason,
        },
    )
