# Guided Workspace Setup

Guided workspace setup is implemented under `/workspace-setup` and
`app.modules.workspace_setup`. It creates an auditable setup run that can configure the minimum
deterministic market-analysis workspace state needed by the web app.

It can create or select:

- Workspace
- Operator user
- Default symbols
- Data source
- Provider credential reference metadata
- Watchlist
- Scanner preset application
- Preference profile
- Optional demo candles from synthetic fixtures
- Product readiness check
- Optional first deterministic scan

It is not a broker setup flow, order-entry flow, auto-trading workflow, trading-alert workflow, or
financial-advice surface.

## Database

The setup module persists two tables:

- `workspace_setup_runs` stores setup status, selected workspace/user, current step, completed,
  skipped and failed step keys, final result metadata, and error state.
- `workspace_setup_step_results` stores one auditable result per step with sanitized input,
  optional output, status, and error state.

Run statuses are `draft`, `running`, `completed`, `completed_with_warnings`, `failed`, and
`cancelled`.

Step keys are `workspace`, `user`, `symbols`, `data_source`, `credential_reference`, `watchlist`,
`scanner_preset`, `preference_profile`, `demo_data`, `readiness_check`, and `first_scan`.

Step result statuses are `pending`, `completed`, `skipped`, and `failed`.

## Settings

```txt
WORKSPACE_SETUP_VERSION=v1
WORKSPACE_SETUP_DEMO_DATA_ENABLED=true
WORKSPACE_SETUP_DEFAULT_MARKET=crypto
WORKSPACE_SETUP_DEFAULT_TIMEFRAMES=1m,5m,15m
```

Demo candle creation is blocked when `WORKSPACE_SETUP_DEMO_DATA_ENABLED=false`.

## API Contracts

```txt
POST /workspace-setup/start
GET /workspace-setup/runs/{setup_run_id}
POST /workspace-setup/runs/{setup_run_id}/steps/{step_key}
POST /workspace-setup/runs/{setup_run_id}/steps/{step_key}/skip
POST /workspace-setup/runs/{setup_run_id}/finish
POST /workspace-setup/demo-workspace
```

Mutating setup endpoints use the existing workspace-admin permission guard. With local
`AUTH_ENABLED=false`, the guard remains a development pass-through.

## Step Behavior

`workspace` creates a workspace by name or selects an existing workspace id.

`user` creates an operator user or selects an existing user id.

`symbols` creates or selects symbols for the selected market and stores the selected symbol ids in
the run result.

`data_source` creates or selects a source. Supported setup source types are CSV, JSON, mock,
provider, and live.

`credential_reference` optionally creates provider credential reference metadata. Raw secrets are
not accepted or returned. The step stores only a `secret_ref` pointer when supplied.

`watchlist` creates a market watchlist from selected symbols and selected timeframes.

`scanner_preset` applies an existing scanner preset when the scanner preset module is available.
Applying a preset creates watchlists or scheduled scan configs only; it does not run a scan.

`preference_profile` creates a review preference profile when the preference profile module is
available.

`demo_data` optionally seeds deterministic candles from synthetic fixtures through the existing JSON
import path. It only runs when explicitly requested and only for safe demo/mock/manual JSON setup
sources.

`readiness_check` runs product readiness when the readiness module is available.

`first_scan` runs a deterministic scan only when explicitly requested. There are no hidden scans.

## Demo Workspace

`POST /workspace-setup/demo-workspace` creates a labeled demo setup run, configures a demo
workspace, operator, crypto symbols, JSON mock source, watchlist, scanner preset if available,
preference profile if available, synthetic candles when enabled, and a readiness check. It does not
run a first scan unless that step is submitted explicitly.

## Safety Boundary

The setup wizard configures deterministic market-analysis data and review workflows only. It does
not connect to brokers for orders, place trades, auto-trade, send trading alerts, or provide
financial advice. Provider credentials are stored as references only; raw provider secrets must stay
in the configured secret manager or environment-specific storage outside this setup API.
