from uuid import UUID

from app.modules.permissions.registry import Permission, permissions_for_role
from app.modules.permissions.schemas import PermissionDefinitionRead, RolePermissionRead
from app.modules.users.models import User, UserRole

PERMISSION_DESCRIPTIONS: dict[Permission, str] = {
    Permission.WORKSPACE_READ: "Read workspace metadata and scoped workspace records.",
    Permission.MARKET_DATA_READ: "Read market data, sources, freshness, and data quality.",
    Permission.ANALYSIS_READ: "Read analysis runs and deterministic analysis artifacts.",
    Permission.SIGNALS_READ: "Read persisted signals and signal context.",
    Permission.OUTCOMES_READ: "Read observed outcome and diagnostic records.",
    Permission.REPORTS_READ: "Read intelligence reports, briefs, and audit timelines.",
    Permission.JOURNAL_READ: "Read journal entries and review reflections.",
    Permission.NOTIFICATIONS_READ: "Read notification events, messages, and channel metadata.",
    Permission.SETTINGS_READ: "Read non-secret workspace settings and registries.",
    Permission.WORKSPACE_WRITE: "Create or update workspace-scoped records.",
    Permission.MARKET_DATA_WRITE: "Create or update market-data source records.",
    Permission.IMPORTS_WRITE: "Import market data into workspace storage.",
    Permission.PROVIDER_POLLING_WRITE: "Create provider polling requests or recovery metadata.",
    Permission.SCANS_WRITE: "Create, update, or run scanner watchlists and scheduled scans.",
    Permission.ANALYSIS_WRITE: "Create or rerun deterministic analysis artifacts.",
    Permission.JOURNAL_WRITE: "Create, update, archive, or review journal records.",
    Permission.NOTIFICATIONS_WRITE: (
        "Create or mutate notification preferences, events, and channels."
    ),
    Permission.PREFERENCES_WRITE: "Create or update user review preference profiles.",
    Permission.ACTION_PLANS_WRITE: "Create, mark, or execute backend-safe action plans.",
    Permission.WORKSPACE_ADMIN: "Perform workspace administrative operations.",
    Permission.USERS_ADMIN: "Create or update workspace users and roles.",
    Permission.CREDENTIALS_ADMIN: (
        "Manage provider, channel, and integration credential references."
    ),
    Permission.STRATEGY_PROFILES_ADMIN: "Govern strategy profile drafts and promotions.",
    Permission.DATA_RETENTION_ADMIN: "Manage and apply data retention policies.",
    Permission.SAFETY_POLICIES_ADMIN: "Manage safety policy settings.",
    Permission.RUNTIME_ADMIN: "Run operational worker or runtime administrative actions.",
}


def get_permissions_for_role(role: UserRole | str) -> frozenset[Permission]:
    return permissions_for_role(role)


def user_has_permission(
    user: User | None,
    permission: Permission | str,
    workspace_id: UUID | None = None,
) -> bool:
    if user is None:
        return False
    try:
        requested_permission = (
            permission if isinstance(permission, Permission) else Permission(str(permission))
        )
    except ValueError:
        return False
    if workspace_id is not None and user.workspace_id != workspace_id:
        return False
    return requested_permission in permissions_for_role(user.role)


def permission_definitions() -> list[PermissionDefinitionRead]:
    return [
        PermissionDefinitionRead(
            permission=permission,
            group=permission.value.rsplit(".", 1)[-1],
            description=PERMISSION_DESCRIPTIONS[permission],
        )
        for permission in Permission
    ]


def role_permission_definitions() -> list[RolePermissionRead]:
    return [
        RolePermissionRead(
            role=role,
            permissions=sorted(permissions, key=lambda permission: permission.value),
        )
        for role, permissions in sorted(
            (
                (UserRole.ADMIN, permissions_for_role(UserRole.ADMIN)),
                (UserRole.ANALYST, permissions_for_role(UserRole.ANALYST)),
                (UserRole.USER, permissions_for_role(UserRole.USER)),
            ),
            key=lambda item: item[0].value,
        )
    ]
