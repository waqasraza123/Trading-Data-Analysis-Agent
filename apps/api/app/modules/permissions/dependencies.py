from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.core.errors import AppError
from app.modules.auth.api_keys import LEGACY_ADMIN_API_KEY_HEADER_NAME, legacy_admin_key_is_valid
from app.modules.auth.dependencies import optional_identity
from app.modules.auth.dependencies import require_permission as auth_require_permission
from app.modules.auth.identity import IdentityContext
from app.modules.auth.settings import auth_is_enforced
from app.modules.permissions.registry import Permission
from app.modules.users.models import User

CURRENT_USER_ID_HEADER = "x-user-id"


async def resolve_current_user_optional(
    identity: Annotated[IdentityContext | None, Depends(optional_identity)],
) -> User | None:
    if identity is None:
        return None
    return identity.user


def enforce_if_auth_enabled(
    request: Request,
    user: User | None,
) -> bool:
    if not auth_is_enforced(request.app.state.settings):
        return False
    if user is not None:
        return True
    if admin_api_key_is_valid(request):
        return True
    raise AppError(401, "authentication_required", "Authentication is required")


def require_permission(
    permission: Permission,
) -> Callable[[Request], Awaitable[None]]:
    return auth_require_permission(permission)


def require_workspace_access(
    workspace_id: UUID,
) -> Callable[[Request, IdentityContext | None], Awaitable[None]]:
    async def dependency(
        request: Request,
        identity: Annotated[IdentityContext | None, Depends(optional_identity)] = None,
    ) -> None:
        if not auth_is_enforced(request.app.state.settings):
            return
        if identity is not None and identity.can_access_workspace(workspace_id):
            return
        raise AppError(403, "workspace_access_denied", "Workspace access denied")

    return dependency


def admin_api_key_is_valid(request: Request) -> bool:
    settings = request.app.state.settings
    supplied_key = request.headers.get(settings.api_key_header_name) or request.headers.get(
        LEGACY_ADMIN_API_KEY_HEADER_NAME,
        "",
    )
    return legacy_admin_key_is_valid(supplied_key, settings)
