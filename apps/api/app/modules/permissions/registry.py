from enum import StrEnum

from app.modules.users.models import UserRole


class Permission(StrEnum):
    WORKSPACE_READ = "workspace.read"
    MARKET_DATA_READ = "market_data.read"
    ANALYSIS_READ = "analysis.read"
    SIGNALS_READ = "signals.read"
    OUTCOMES_READ = "outcomes.read"
    REPORTS_READ = "reports.read"
    JOURNAL_READ = "journal.read"
    NOTIFICATIONS_READ = "notifications.read"
    SETTINGS_READ = "settings.read"
    WORKSPACE_WRITE = "workspace.write"
    MARKET_DATA_WRITE = "market_data.write"
    IMPORTS_WRITE = "imports.write"
    PROVIDER_POLLING_WRITE = "provider_polling.write"
    SCANS_WRITE = "scans.write"
    ANALYSIS_WRITE = "analysis.write"
    JOURNAL_WRITE = "journal.write"
    NOTIFICATIONS_WRITE = "notifications.write"
    PREFERENCES_WRITE = "preferences.write"
    ACTION_PLANS_WRITE = "action_plans.write"
    WORKSPACE_ADMIN = "workspace.admin"
    USERS_ADMIN = "users.admin"
    CREDENTIALS_ADMIN = "credentials.admin"
    STRATEGY_PROFILES_ADMIN = "strategy_profiles.admin"
    DATA_RETENTION_ADMIN = "data_retention.admin"
    SAFETY_POLICIES_ADMIN = "safety_policies.admin"
    RUNTIME_ADMIN = "runtime.admin"


READ_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.WORKSPACE_READ,
        Permission.MARKET_DATA_READ,
        Permission.ANALYSIS_READ,
        Permission.SIGNALS_READ,
        Permission.OUTCOMES_READ,
        Permission.REPORTS_READ,
        Permission.JOURNAL_READ,
        Permission.NOTIFICATIONS_READ,
        Permission.SETTINGS_READ,
    }
)

USER_READ_PERMISSIONS: frozenset[Permission] = frozenset(
    {
        Permission.WORKSPACE_READ,
        Permission.MARKET_DATA_READ,
        Permission.ANALYSIS_READ,
        Permission.SIGNALS_READ,
        Permission.OUTCOMES_READ,
        Permission.REPORTS_READ,
        Permission.JOURNAL_READ,
        Permission.NOTIFICATIONS_READ,
        Permission.SETTINGS_READ,
    }
)

ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.ADMIN: frozenset(Permission),
    UserRole.ANALYST: frozenset(
        {
            *READ_PERMISSIONS,
            Permission.ANALYSIS_WRITE,
            Permission.SCANS_WRITE,
            Permission.JOURNAL_WRITE,
            Permission.PREFERENCES_WRITE,
        }
    ),
    UserRole.USER: frozenset(
        {
            *USER_READ_PERMISSIONS,
            Permission.SCANS_WRITE,
            Permission.JOURNAL_WRITE,
            Permission.PREFERENCES_WRITE,
        }
    ),
}


def all_permissions() -> list[Permission]:
    return list(Permission)


def permissions_for_role(role: UserRole | str) -> frozenset[Permission]:
    try:
        normalized_role = role if isinstance(role, UserRole) else UserRole(str(role))
    except ValueError:
        return frozenset()
    return ROLE_PERMISSIONS.get(normalized_role, frozenset())
