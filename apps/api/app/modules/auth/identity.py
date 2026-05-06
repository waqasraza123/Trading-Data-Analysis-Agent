from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.core.errors import AppError
from app.modules.auth.models import AuthApiKey, AuthIdentity, AuthIdentityStatus
from app.modules.auth.schemas import (
    AuthUserRead,
    AuthWorkspaceRead,
    CurrentIdentityRead,
    IdentitySource,
)
from app.modules.permissions.registry import Permission, permissions_for_role
from app.modules.users.models import User, UserRole
from app.modules.users.repository import UserRepository
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.repository import WorkspaceRepository


@dataclass(frozen=True)
class IdentityContext:
    source: IdentitySource
    provider: str | None = None
    provider_subject: str | None = None
    user: User | None = None
    workspace: Workspace | None = None
    api_key: AuthApiKey | None = None
    scopes: list[str] = field(default_factory=list)
    admin: bool = False

    @property
    def workspace_id(self) -> UUID | None:
        if self.workspace is not None:
            return self.workspace.id
        if self.user is not None:
            return self.user.workspace_id
        if self.api_key is not None:
            return self.api_key.workspace_id
        return None

    @property
    def permissions(self) -> frozenset[Permission]:
        if self.admin:
            return frozenset(Permission)
        if self.user is None:
            return scoped_permissions(self.scopes)
        return permissions_for_role(self.user.role)

    def can_access_workspace(self, workspace_id: UUID | None) -> bool:
        if workspace_id is None or self.admin:
            return True
        current_workspace_id = self.workspace_id
        return current_workspace_id is not None and current_workspace_id == workspace_id

    def has_permission(self, permission: Permission, workspace_id: UUID | None = None) -> bool:
        if not self.can_access_workspace(workspace_id):
            return False
        if self.admin:
            return True
        if permission in self.permissions:
            return True
        return "*" in self.scopes or permission.value in self.scopes


async def build_dev_identity(
    *,
    settings: Settings,
    session: AsyncSession,
    user_id_header: str | None,
    workspace_id_header: str | None,
) -> IdentityContext | None:
    user_id = parse_uuid(user_id_header)
    workspace_id = parse_uuid(workspace_id_header or settings.auth_dev_workspace_id)
    user: User | None = None
    workspace: Workspace | None = None
    if user_id is not None:
        user = await UserRepository(session).get_by_id(user_id)
        if user is None:
            raise AppError(401, "invalid_user_context", "User context is invalid")
        workspace_id = user.workspace_id
    elif settings.auth_dev_user_email and workspace_id is not None:
        user = await UserRepository(session).get_by_workspace_email(
            workspace_id,
            settings.auth_dev_user_email,
        )
    if workspace_id is not None:
        workspace = await WorkspaceRepository(session).get_by_id(workspace_id)
        if workspace is None:
            raise AppError(401, "invalid_workspace_context", "Workspace context is invalid")
    if user is None and workspace is None:
        return None
    return IdentityContext(
        source=IdentitySource.DEV,
        user=user,
        workspace=workspace,
        admin=user is not None and user.role == UserRole.ADMIN.value,
    )


async def build_api_key_identity(
    *,
    session: AsyncSession,
    validation_api_key: AuthApiKey | None,
    legacy_admin: bool,
) -> IdentityContext:
    if legacy_admin:
        return IdentityContext(source=IdentitySource.LEGACY_ADMIN_API_KEY, admin=True)
    if validation_api_key is None:
        raise AppError(401, "invalid_credentials", "Credentials are invalid")
    workspace = None
    if validation_api_key.workspace_id is not None:
        workspace = await WorkspaceRepository(session).get_by_id(validation_api_key.workspace_id)
        if workspace is None:
            raise AppError(401, "invalid_credentials", "Credentials are invalid")
    scopes = [str(scope) for scope in validation_api_key.scopes_json]
    return IdentityContext(
        source=IdentitySource.API_KEY,
        workspace=workspace,
        api_key=validation_api_key,
        scopes=scopes,
        admin="*" in scopes,
    )


async def build_jwt_identity(
    *,
    session: AsyncSession,
    claims: dict[str, object],
    settings: Settings,
) -> IdentityContext:
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject.strip():
        raise AppError(401, "invalid_token", "Token subject is missing")
    provider = str(claims.get("iss") or settings.jwt_issuer or "jwt")
    statement = select(AuthIdentity).where(
        AuthIdentity.provider == provider,
        AuthIdentity.provider_subject == subject,
        AuthIdentity.status == AuthIdentityStatus.ACTIVE.value,
    )
    result = await session.execute(statement)
    auth_identity = result.scalar_one_or_none()
    if auth_identity is None:
        raise AppError(401, "identity_not_linked", "Identity is not linked")
    user = await UserRepository(session).get_by_id(auth_identity.user_id)
    workspace = await WorkspaceRepository(session).get_by_id(auth_identity.workspace_id)
    if user is None or workspace is None or user.workspace_id != workspace.id:
        raise AppError(401, "invalid_identity_context", "Identity context is invalid")
    return IdentityContext(
        source=IdentitySource.JWT,
        provider=auth_identity.provider,
        provider_subject=auth_identity.provider_subject,
        user=user,
        workspace=workspace,
        admin=user.role == UserRole.ADMIN.value,
    )


def identity_to_read(identity: IdentityContext | None) -> CurrentIdentityRead:
    if identity is None:
        return CurrentIdentityRead(authenticated=False)
    user = None
    if identity.user is not None:
        user = AuthUserRead(
            id=identity.user.id,
            workspace_id=identity.user.workspace_id,
            email=identity.user.email,
            name=identity.user.name,
            role=UserRole(identity.user.role),
        )
    workspace = None
    if identity.workspace is not None:
        workspace = AuthWorkspaceRead(id=identity.workspace.id, name=identity.workspace.name)
    return CurrentIdentityRead(
        authenticated=True,
        source=identity.source,
        provider=identity.provider,
        provider_subject=identity.provider_subject,
        user=user,
        workspace=workspace,
        permissions=sorted(identity.permissions, key=lambda item: item.value),
        scopes=identity.scopes,
        admin=identity.admin,
    )


def scoped_permissions(scopes: list[str]) -> frozenset[Permission]:
    if "*" in scopes:
        return frozenset(Permission)
    permissions: set[Permission] = set()
    for scope in scopes:
        try:
            permissions.add(Permission(scope))
        except ValueError:
            continue
    return frozenset(permissions)


def parse_uuid(value: str | None) -> UUID | None:
    if value is None or not value.strip():
        return None
    try:
        return UUID(value.strip())
    except ValueError as error:
        raise AppError(401, "invalid_user_context", "User context is invalid") from error
