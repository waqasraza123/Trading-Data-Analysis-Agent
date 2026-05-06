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

## Auth Behavior

When `AUTH_MODE=dev` and `AUTH_ENABLED=false`, permission dependencies allow requests
through. This is the local and test default and preserves current development workflows.

For production modes, permissions run after `app.modules.auth` resolves a dev,
API-key, JWT, or mixed identity. The legacy configured admin API key remains accepted
as an admin principal. Dev context can be supplied with `x-user-id` and
`x-workspace-id`; JWT providers should link subjects in `auth_identities`.

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
- production auth API-key management
- live subscription writes and provider event ingestion
- data quality, candle gap recovery, daily workflow, daily brief, signal digest,
  setup context, market memory, read model rebuild, runtime supervisor, product
  readiness, and symbol administration writes

Read endpoints mostly preserve existing behavior unless they are later migrated
behind explicit read permissions.

## Future Auth Integration

Future OAuth/session integrations should map their provider subject to
`auth_identities`, then reuse the same `Permission` registry and workspace checks.
The API-key path should remain a service/admin principal, not a user impersonation
mechanism.
