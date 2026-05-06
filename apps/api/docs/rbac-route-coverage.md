# RBAC Route Coverage

This table classifies current route protection for auth hardening. Health and read-only inspection routes remain public unless a future product requirement makes workspace reads private.

| Area | Classification | Enforcement |
| --- | --- | --- |
| `/health` | public | No identity required |
| `/auth/me`, `/auth/context` | public/dev-aware | Returns resolved context; enforced modes require credentials for `/auth/me` |
| `/auth/api-keys*` | admin | `require_admin` |
| Workspace setup mutations | admin | `workspace.admin` |
| Workspace and user mutations | admin/write | `workspace.admin`, `workspace.write`, `users.admin` |
| Provider credentials and connection tests | admin | `credentials.admin` |
| Data sources | admin | `credentials.admin` |
| Imports | workspace_write | `imports.write` |
| Provider polling and gap recovery writes | workspace_write | `provider_polling.write` |
| Provider health refresh and recovery prep | workspace_write | `market_data.write`, `provider_polling.write` |
| Live subscription writes and event ingestion | workspace_write/internal_worker | `market_data.write`, `provider_polling.write` |
| Data-quality runs | workspace_write | `market_data.write` |
| Analysis lifecycle create/replay/classify/retry | workspace_write | `analysis.write` |
| Daily workflows, routines, scans, scanner presets | workspace_write/admin | `scans.write`, `runtime.admin` |
| Daily briefs, signal digests, setup context, market memory, read-model rebuilds | workspace_write | `analysis.write` |
| Journal entries | workspace_write | `journal.write` |
| Notifications, channels, inbox state, dispatch | workspace_write/admin | `notifications.write`, `credentials.admin` |
| Strategy profile governance | admin | `strategy_profiles.admin` |
| Action-plan execution endpoints | workspace_write | `action_plans.write` |
| Data retention policies and apply | admin | `data_retention.admin` |
| Runtime supervisor mutations | admin/internal_worker | `runtime.admin` |
| Product readiness run | admin | `workspace.admin` |
| Symbols | admin | `workspace.admin` |

Read-only artifact routes are still available for the current dashboard and operator cockpit. The next tightening pass should make workspace read routes depend on `workspace.read` once a frontend login/session flow exists.
