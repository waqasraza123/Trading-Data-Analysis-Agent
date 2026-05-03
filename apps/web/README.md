# Daily Trading Dashboard Web App

Read-only Next.js dashboard for deterministic market intelligence. The app is an operator cockpit for daily analysis over backend artifacts; it is not a broker terminal, auto-trading system, execution workflow, or financial-advice surface.

## Purpose

The dashboard makes the first usable product surface over the FastAPI backend:

- Watchlist symbols and timeframes.
- Current deterministic bias and latest signal context.
- Confidence labels, setup quality, evidence, risk notes, and invalidation context when the backend provides them.
- Market regime, market session, market-memory freshness, and data quality.
- Recent outcome observations by horizon.
- Backend follow-up action items.
- API health, worker status, failed fetch states, and last refreshed timestamp.

## Backend Endpoints Used

The client composes data from optional backend APIs:

- `GET /health`
- `GET /health/workers`
- `GET /workspaces`
- `GET /symbols`
- `GET /symbols/{symbol_id}`
- `GET /market-watchlists`
- `GET /market-watchlists/{watchlist_id}/items`
- `GET /market-memory/snapshots`
- `GET /scheduled-scan-configs`
- `GET /scheduled-scan-configs/due`
- `GET /analysis-runs`
- `GET /analysis-runs/{analysis_run_id}/signal`
- `GET /signals/{signal_id}`
- `GET /signals/{signal_id}/outcomes`
- `GET /signals/{signal_id}/market-regime`
- `GET /signals/{signal_id}/market-session`
- `GET /decision-readiness/signals/{signal_id}/latest`
- `GET /intelligence-reports/signals/{signal_id}`
- `GET /audit-timeline/signals/{signal_id}`
- `GET /action-items/due`

Missing optional endpoints render empty states or backend-state warnings instead of crashing the page.

## Environment

Create `apps/web/.env.local` when local defaults are not enough:

```sh
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_APP_NAME=Daily Trading Dashboard
```

Only public frontend configuration belongs in this file. Backend secrets, API keys, database URLs, and worker credentials must stay in backend environment files.

## Run

From `apps/web`:

```sh
npm install
npm run dev
```

Open:

```txt
http://127.0.0.1:3000/dashboard
```

Use `?workspaceId=<workspace-id>` to pin a workspace and `?signalId=<signal-id>` to focus a dashboard signal.

## Routes

- `/dashboard` renders the daily operator cockpit.
- `/signals/[signalId]` renders a read-only signal report, falling back to individual signal APIs when report data is unavailable.
- `/symbols/[symbolId]` renders symbol/timeframe state, market memory, recent signals, outcomes, scheduled scans, and analysis runs.

## Safety Language

The UI uses market-intelligence wording such as bias, review recommended, data stale, evidence conflict, follow-through observed, reversal observed, setup context, invalidation context, and watch next candle close. It avoids direct order instructions, certainty claims, broker execution prompts, and account-outcome language.

## Fallback Behavior

The dashboard expects backend modules to be deployed incrementally:

- If market memory is unavailable, watchlists and symbols still render.
- If reports are unavailable, signal pages use signal, evidence, confidence, outcomes, readiness, context, and audit endpoints individually.
- If readiness is unavailable, readiness panels hide behind safe empty states.
- If scans are unavailable, scan panels render empty states.
- If API or worker health fails, backend state shows the failed fetch without blocking the rest of the UI.
