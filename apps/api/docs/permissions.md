# Workspace RBAC and Route Permissions

The API includes a backend-only permission layer under `app.modules.permissions`.
It is intentionally static in this phase because the project does not yet have an
external identity provider, session model, or role-management UI.

## Roles

- `admin`: all permissions.
- `analyst`: all read permissions plus analysis, scan, journal, and preference writes.
- `user`: read access plus journal, preference, and safe scanner writes.

## Permission Groups

Read permissions:

- `workspace.read`
- `market_data.read`
- `analysis.read`
- `signals.read`
- `outcomes.read`
- `reports.read`
- `journal.read`
- `notifications.read`
- `settings.read`

Write permissions:

- `workspace.write`
- `market_data.write`
- `imports.write`
- `provider_polling.write`
- `scans.write`
- `analysis.write`
- `journal.write`
- `notifications.write`
- `preferences.write`
- `action_plans.write`

Admin permissions:

- `workspace.admin`
- `users.admin`
- `credentials.admin`
- `strategy_profiles.admin`
- `data_retention.admin`
- `safety_policies.admin`
- `runtime.admin`

## AUTH_ENABLED Behavior

When `AUTH_ENABLED=false`, permission dependencies allow requests through. This is
the local and test default and preserves current development workflows.

When `AUTH_ENABLED=true`, mutating requests still use the existing API-key guard.
The permission dependency also accepts that configured admin API key as an admin
principal. Optional user context can be supplied with `x-user-id` for future
integration, but this is not a standalone authentication provider.

Permission failures return standard API errors:

- `authentication_required`
- `invalid_user_context`
- `permission_denied`
- `workspace_access_denied`

The dependency logs structured permission-failure audit events with request ID,
path, method, permission, user ID, user role, and workspace ID when available. It
does not log API keys or secret values.

## Route Dependency Pattern

Use route-level dependencies for protected backend mutations:

```python
from fastapi import Depends

from app.modules.permissions.dependencies import require_permission
from app.modules.permissions.registry import Permission


@router.post(
    "/example",
    dependencies=[Depends(require_permission(Permission.SCANS_WRITE))],
)
async def create_example() -> ExampleRead:
    ...
```

Use `user_has_permission(user, permission, workspace_id)` inside services when
future user-context auth needs object-level workspace checks after loading a
workspace-scoped record.

## Protected Route Surface

This phase applies permissions to focused high-impact write routes:

- user administration
- workspace writes
- data source and provider credential writes
- candle imports
- provider polling request creation
- provider health refresh and gap-recovery preparation
- scanner watchlist/config writes and scan execution
- scanner preset seed/apply writes
- strategy profile governance and promotion
- preference profile writes
- journal writes
- notification preference, channel, event, message, and dispatch mutations
- backend-safe action-plan creation/execution mutations
- data retention policy and apply mutations

Read endpoints mostly preserve existing behavior unless they are later migrated
behind explicit read permissions.

## Future Auth Integration

Future OAuth/JWT/session integration should replace `x-user-id` resolution with a
validated identity principal, then reuse the same `Permission` registry and
`user_has_permission` workspace checks. The current API-key path should remain a
service/admin principal, not a user impersonation mechanism.
