# RBAC Route Coverage

This document classifies current route protection for auth hardening. Health and read-only inspection routes remain public unless a future product requirement makes workspace reads private.

| Area | Classification | Enforcement |
| --- | --- | --- |
| `/health` | public | No identity required |
| `/auth/me`, `/auth/context` | public/dev-aware | Returns resolved context; enforced modes require credentials for `/auth/me` |
| `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/password/change`, `/auth/sessions*` | auth self-service | Credential exchange or session-authenticated user self-service |
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

## Mutating Route Permission Map

All `POST`, `PUT`, `PATCH`, and `DELETE` routes under `app/modules/**/routes.py` must either declare a route-level `Depends(require_permission(...))`, declare `Depends(require_admin())`, or appear in the explicit exemption list below. The regression test in `app/tests/unit/test_rbac_route_coverage.py` enforces this.

| Permission | Mutating route families |
| --- | --- |
| `admin-api-key` | `/auth/api-keys*` |
| `action_plans.write` | Reasoning action-plan creation and due action item execution/marking routes |
| `analysis.write` | Analysis lifecycle, daily briefs, advanced features, market regime/session context, multi-timeframe/cross-asset context, signal digests, signal priority scoring, outcome evaluation, setup context, market memory, drift/diagnostic/backtest/walk-forward runs, reasoning/scenario routes, read model rebuilds, deterministic/LLM explanation generation, news correlation, event studies, intelligence catalog/dataset/quality/AI routes, chart screenshot run/review creation, operator review mutations, artifact graph mutations, and decision readiness assessment routes |
| `credentials.admin` | Data-source mutations, provider credential mutations/tests, notification channel mutations, and equity provider connection tests |
| `data_retention.admin` | Data retention policy and retention run mutation routes |
| `imports.write` | Candle JSON/CSV import routes |
| `journal.write` | Journal entry create/update/archive/attachment/review routes |
| `market_data.write` | Equity data import/enrichment routes, equity research catalyst mutations, provider health refreshes, live subscription mutations, data-quality runs, and news event create/import/update routes |
| `notifications.write` | Notification preferences/events/delivery/inbox mutations and webhook subscription/outbox event mutations |
| `preferences.write` | Preference profile create/update/archive/default/match routes |
| `provider_polling.write` | Provider polling requests, gap recovery preparation/cancel routes, live feed event ingestion, and backfill plan create/cancel routes |
| `runtime.admin` | Observability SLO snapshots, runtime/daily routine/capability/engine/rule-pack/scanner/state/data-contract/job-queue seed or operational routes, intelligence metric snapshots, operator playbook operations, synthetic fixture generation, engine execution create/cancel, and job queue create/cancel routes |
| `safety_policies.admin` | Safety policy seed routes |
| `scans.write` | Workspace quick actions, daily workflow/routine scan runs, equity research universe/scan mutations, watchlist/scheduled scan mutations, and scanner preset application routes |
| `strategy_profiles.admin` | Strategy profile governance, profile simulations, profile recommendation status updates, rule-pack create and reproducibility manifest generation routes |
| `users.admin` | User create/update routes |
| `workspace.admin` | Workspace create, onboarding actions, workspace setup flows, symbol mutations, demo mode workspace/flow routes, and product readiness run routes |
| `workspace.write` | Workspace update routes |

## Explicit Exemptions

These `POST` routes intentionally do not declare `require_permission(...)` because they are either write-free validation/preview operations or auth self-service endpoints where route-level RBAC would block account bootstrap, credential exchange, or session-authenticated user credential/session maintenance. They remain covered by their local validation, session identity dependencies, or the global auth/API-key middleware behavior where applicable.

| Route | Reason |
| --- | --- |
| `POST /auth/login` | Credential exchange endpoint |
| `POST /auth/logout` | Self-service session revocation |
| `POST /auth/password/change` | Self-service password credential rotation |
| `POST /auth/register` | First-party account bootstrap endpoint |
| `POST /auth/sessions/revoke-other` | Self-service session revocation |
| `POST /auth/sessions/{session_id}/revoke` | Self-service session revocation |
| `POST /chart-screenshot-runs/image/preview` | Write-free image extraction preview |
| `POST /data-contracts/validate` | Payload validation only |
| `POST /data-contracts/validate-source` | Source payload validation only |
| `POST /safety-policies/evaluate-action` | Policy evaluation only |
| `POST /safety-policies/evaluate-payload` | Policy evaluation only |
| `POST /safety-policies/evaluate-text` | Policy evaluation only |
| `POST /state-machines/validate-transition` | Transition validation only |
