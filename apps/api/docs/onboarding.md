# First-Run Onboarding

First-run onboarding is implemented under `/onboarding` and `app.modules.onboarding`. It composes
existing workspace setup, product readiness, demo mode, symbols, data sources, provider health,
watchlists, scanner configs, and daily workflow state into one operator-facing status response.

It adds no database tables. `GET /onboarding/status` is read-only and does not create a workspace,
seed data, poll providers, run scans, start workers, send notifications, execute broker actions,
auto-trade, or provide financial advice.

## API

```txt
GET /onboarding/status?workspaceId=<optional>&userId=<optional>
POST /onboarding/actions
GET /workspaces/default-context
```

`/workspaces/default-context` returns the selected dev identity workspace when dev headers are
present, otherwise the first available workspace. It returns `missing_workspace` when none exists
and never creates records from a GET.

## Status Response

The status response includes:

- Readiness label, score, and summary.
- Workspace and operator context.
- Symbol, data source, data freshness, watchlist, and scan config counts.
- Daily workflow availability.
- Demo mode availability.
- One exact next step.
- Ordered setup steps with complete, incomplete, warning, blocked, or unavailable state.
- Warnings and missing sections.

## Actions

Allowed actions are explicit:

- `create_workspace`
- `create_user`
- `seed_symbols`
- `seed_default_data_sources`
- `create_basic_watchlist`
- `create_basic_scan_config`
- `run_readiness_check`
- `run_demo_flow`

Actions reuse existing services where possible. Unsupported action types are rejected. Demo flow is
available only when demo mode is enabled or the app environment is development. Provider credential
creation and external provider polling are not hidden behind onboarding actions.

## Safety Boundary

Onboarding is a setup and readiness UX for deterministic analysis. It does not execute broker
orders, connect to brokers for orders, auto-trade, copy-trade, send external signal delivery,
calculate account results, or provide financial advice.
