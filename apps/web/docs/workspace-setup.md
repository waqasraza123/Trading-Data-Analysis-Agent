# Guided Workspace Setup

The setup wizard lives at `/setup`. It is a step-by-step operator workflow over the backend
`/workspace-setup` API and is intended to make a fresh workspace usable without knowing every
backend module.

## UI Flow

The wizard starts a backend setup run, saves each step to the backend, and can resume from the run
state returned by the API.

Steps:

- Workspace
- Operator
- Symbols
- Data source
- Credential reference
- Watchlist
- Scanner preset
- Preference profile
- Demo data
- Readiness check
- First scan
- Summary

Optional steps can be skipped. Required steps validate locally before submission. The page also
offers a demo workspace action that asks the backend to build a safe synthetic workspace flow.

## Navigation

The shared navigation includes Setup under the readiness section. Product readiness remediation
links for missing workspace, user, seed, symbols, sources, watchlists, and scan configuration point
to `/setup`.

When setup finishes, the summary links to `/command-center?workspaceId=<workspace-id>` when the
backend result contains a workspace id.

## Safe UI Behavior

The credential step accepts provider reference metadata only. It does not ask for provider API keys,
tokens, passwords, webhook secrets, broker credentials, or account credentials.

Demo data is explicit. The UI sends a request to seed synthetic candles only when the operator
selects demo candles.

The first scan is explicit. The UI requires a checkbox before submitting the first scan step and
does not trigger scans through hidden page loads or summary rendering.

Copy stays non-advisory. The wizard describes setup, review, readiness, observations, and
deterministic scans. It does not use broker, order, auto-trading, trading-alert, buy/sell, or
financial-advice language.

## Frontend Files

- `app/setup/page.tsx`
- `src/components/setup-wizard/*`
- `src/lib/api/workspaceSetup.ts`
- `src/lib/setup-wizard/types.ts`
- `src/lib/setup-wizard/validation.ts`

## Backend API

```txt
POST /workspace-setup/start
GET /workspace-setup/runs/{setup_run_id}
POST /workspace-setup/runs/{setup_run_id}/steps/{step_key}
POST /workspace-setup/runs/{setup_run_id}/steps/{step_key}/skip
POST /workspace-setup/runs/{setup_run_id}/finish
POST /workspace-setup/demo-workspace
```

Missing optional backend modules are shown as skipped or warning states from the backend setup run
instead of crashing the page.
