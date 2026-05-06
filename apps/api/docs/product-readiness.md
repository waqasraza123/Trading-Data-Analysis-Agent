# Product Readiness

Product readiness is an operator-facing checklist for daily-use setup. It validates whether the API,
database, seed data, workspace records, data freshness, scanner setup, workers, optional
notifications, and journal surfaces are ready for review.

It is read-only except for persisting the readiness run itself. It does not seed data, run scans,
start workers, run daily workflows, call market-data providers, send notifications, execute broker
actions, auto-trade, copy-trade, or provide financial advice.

## Storage

Readiness runs are persisted in `product_readiness_runs`.

Important fields:

- `workspace_id`: nullable workspace scope.
- `status`: `completed`, `completed_with_warnings`, or `failed`.
- `readiness_version`: settings-backed checklist version.
- `readiness_score`: normalized `0..1` score.
- `readiness_label`: `ready`, `needs_setup`, `degraded`, `blocked`, or `unknown`.
- `checks_json`: full check payloads.
- `blockers_json`: failed checks.
- `warnings_json`: warning checks.

## API

```txt
POST /product-readiness/run
GET /product-readiness/latest
GET /product-readiness/runs
GET /product-readiness/runs/{run_id}
```

`workspaceId` is optional on run, latest, and list requests. A run with a workspace ID validates
workspace-scoped setup; a run without one validates global API/database state where possible.

## Checks

- `api_health`
- `database_connection`
- `migration_head_known`
- `seed_data_present`
- `workspace_present`
- `user_present`
- `symbols_present`
- `data_sources_present`
- `provider_credentials_status`
- `provider_health_available`
- `read_model_availability`
- `fresh_candles_available`
- `watchlist_configured`
- `scan_configured`
- `daily_workflow_available`
- `runtime_supervisor_status`
- `worker_health_available`
- `notification_channels_optional`
- `journal_available`
- `web_api_configured`
- `no_critical_stale_or_missing_data`

Each check returns:

- `key`
- `status`: `passed`, `warning`, `failed`, or `skipped`
- `title`
- `summary`
- `remediation`
- `related_route`
- `metadata`

## Remediation

Readiness responses point to existing operator surfaces:

- `/data/onboarding` for source, symbol, candle, provider health, freshness, and gap checks.
- `/scanner` for watchlists, scanner presets, and scheduled scan configs.
- `/preferences/strategy` for operator/user preference setup.
- `/notifications` for optional notification channel review.
- `/command-center` for explicit daily workflow runs.
- `/journal` for operator notes and outcome reflection.

## Integration Scope

The readiness run reads persisted provider credential reference status, provider health snapshots,
read model counts, runtime supervisor definitions/instances/run requests, live worker health,
workspace setup, symbols, data sources, candles, watchlists, scans, optional notifications, and
journal state. Read model checks treat snapshots as rebuildable acceleration data, not source of
truth. Runtime checks inspect persisted worker state only and do not start workers.

## Safety Boundary

The checklist validates readiness only. It never runs hidden workflows, never enables alerts by
default, never sends external notifications, and never performs broker or order actions. Any setup
or workflow mutation remains an explicit action on its owning route.
