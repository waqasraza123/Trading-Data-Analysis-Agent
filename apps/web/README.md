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
- Signal triage board for deterministic prioritization.
- Workspace daily brief composition for "what should I review now?"
- API health, worker status, failed fetch states, and last refreshed timestamp.
- Live data onboarding for source selection, symbol/timeframe readiness, freshness checks, gap planning, and prepare-only recovery metadata.
- Watchlist scanner controls for backend deterministic scan configuration, due scans, run-now execution, scan run item review, and produced signal review.
- Outcome review and journal loop for turning observed outcomes into daily reflection notes and reliability review.

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
- `POST /scheduled-scan-configs`
- `PATCH /scheduled-scan-configs/{scan_config_id}`
- `POST /scheduled-scan-configs/{scan_config_id}/pause`
- `POST /scheduled-scan-configs/{scan_config_id}/resume`
- `POST /scheduled-scan-configs/{scan_config_id}/archive`
- `POST /scheduled-scan-configs/{scan_config_id}/run`
- `POST /scheduled-scan-configs/run-due`
- `GET /scheduled-scan-runs/{scan_run_id}`
- `GET /scheduled-scan-runs/{scan_run_id}/items`
- `POST /market-watchlists`
- `PATCH /market-watchlists/{watchlist_id}`
- `POST /market-watchlists/{watchlist_id}/items`
- `PATCH /market-watchlist-items/{item_id}`
- `DELETE /market-watchlist-items/{item_id}`
- `GET /analysis-runs`
- `GET /analysis-runs/{analysis_run_id}/signal`
- `GET /signals/{signal_id}`
- `GET /signals/{signal_id}/priority-score`
- `GET /signals/{signal_id}/outcomes`
- `GET /signals/{signal_id}/setup-context`
- `GET /signals/{signal_id}/multi-timeframe-context`
- `GET /signals/{signal_id}/cross-asset-context`
- `GET /cross-asset-context/runs/{run_id}/results`
- `GET /signals/{signal_id}/reasoning/scenarios/latest`
- `POST /signals/{signal_id}/historical-cases/search`
- `GET /signals/{signal_id}/market-regime`
- `GET /signals/{signal_id}/market-session`
- `GET /decision-readiness/signals/{signal_id}/latest`
- `GET /decision-readiness`
- `GET /operator-reviews`
- `GET /intelligence-quality/signals/{signal_id}/latest`
- `GET /intelligence-reports/signals/{signal_id}`
- `GET /audit-timeline/signals/{signal_id}`
- `GET /action-items/due`
- `GET /signal-digests`
- `GET /signal-digests/{digest_id}/items`
- `GET /outcomes/performance/patterns`
- `GET /profile-diagnostics/strategy-profiles`
- `GET /profile-diagnostics/patterns`
- `GET /profile-diagnostics/recommendations`
- `GET /confidence-calibration/runs`
- `GET /confidence-calibration/runs/{run_id}/bins`
- `GET /cohort-drift/results/recent`
- `GET /pattern-attribution/runs`
- `GET /pattern-attribution/runs/{run_id}/results`
- `GET /journal-entries`
- `POST /journal-entries`
- `GET /journal-entries/{entry_id}`
- `PATCH /journal-entries/{entry_id}`
- `POST /journal-entries/{entry_id}/archive`
- `GET /journal-entries/{entry_id}/reviews`
- `POST /journal-entries/{entry_id}/review`
- `GET /data-sources`
- `POST /data-sources`
- `GET /candles/latest`
- `GET /candles/count`
- `GET /candles/quality`
- `GET /live/subscriptions`
- `GET /provider-polling/requests`
- `POST /data-quality/candle-range/run`
- `POST /candle-gap-recovery/plans`
- `GET /candle-gap-recovery/plans/{plan_id}/items`
- `POST /candle-gap-recovery/plans/{plan_id}/prepare-provider-polling`

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
http://127.0.0.1:3000/brief
http://127.0.0.1:3000/scanner
http://127.0.0.1:3000/triage
http://127.0.0.1:3000/review/outcomes
http://127.0.0.1:3000/journal
http://127.0.0.1:3000/data/onboarding
```

Use `?workspaceId=<workspace-id>` to pin a workspace and `?signalId=<signal-id>` to focus a dashboard signal.
Use `/brief?workspaceId=<workspace-id>` to review the current workspace brief.
Use `/scanner?workspaceId=<workspace-id>` to manage watchlists and scheduled scan configs. A returned scan run can be opened with `?runId=<scan-run-id>`.
Use `/triage?workspaceId=<workspace-id>` to review deterministic signals by triage column. Filters support workspace, symbol, timeframe, bias, confidence, triage column, data freshness, profile key, only fresh, and only review required.
Use `/review/outcomes?workspaceId=<workspace-id>` to review recent signal outcomes, linked journal notes, and optional diagnostics.
Use `/journal?workspaceId=<workspace-id>` to create and review reflection notes. Optional `signalId`, `analysisRunId`, `setupContextId`, and `outcomeId` query params prefill context links.
Use `/data/onboarding?workspaceId=<workspace-id>` for the data-source onboarding workflow. The page persists selected workspace, source, symbols, and timeframes in the URL and browser storage.

## Routes

- `/dashboard` renders the daily operator cockpit.
- `/scanner` renders watchlist scanner controls for backend deterministic scan orchestration.
- `/triage` renders the read-only signal triage board over deterministic signal artifacts.
- `/review/outcomes` renders the outcome and journal review loop over recent signal outcomes.
- `/journal` and `/journal/[entryId]` render reflection note creation, editing, archival, and outcome review when supported by the journal API.
- `/data/onboarding` renders the live data onboarding and freshness workflow.
- `/brief` renders the workspace daily brief, composed in the web client layer from existing optional backend endpoints.
- `/signals/[signalId]` renders a full read-only setup detail view, preferring the intelligence report and falling back to individual signal, setup, evidence, confidence, outcome, readiness, context, reasoning, historical-case, quality, audit, and journal APIs when report data is unavailable.
- `/symbols/[symbolId]` renders symbol/timeframe state, market memory, recent signals, outcomes, scheduled scans, and analysis runs.

## Daily Workflow Loop

The integrated web surface is arranged for a deterministic daily review loop:

1. Ingest or verify fresh data in `/data/onboarding`.
2. Run deterministic watchlist scans in `/scanner`.
3. Review the workspace cockpit in `/brief`.
4. Triage stored signals in `/triage`.
5. Inspect setup context in `/signals/[signalId]`.
6. Review observed outcomes in `/review/outcomes`.
7. Add or update observational journal notes in `/journal`.
8. Revisit observed outcomes and digest summaries in `/brief`, `/dashboard`, or symbol detail.

The shared navigation links Dashboard, Brief, Triage, Scanner, Outcome Review, Journal, and Data Onboarding. Workspace-aware links preserve `workspaceId` where the source page knows it. Stale-data and data-quality sections link back to onboarding; scan-result and triage cards link to setup detail; outcome cards link to journal prompts; symbol pages link back into scanner and onboarding.

## Outcome Review Loop

The outcome review page is a frontend composition layer in `apps/web/src/lib/api/outcomeReview.ts`. It does not add a backend endpoint. Because the backend exposes outcomes by signal and analysis run rather than a workspace-wide outcome queue, the page loads recent analysis runs, resolves their deterministic signals, loads each signal's outcomes, and links any matching journal entries.

The page shows:

- Recent observed outcomes by signal, horizon, outcome label, pattern, bias, and linked setup context when available.
- Outcome labels using safe review language: observed continuation, observed reversal, no follow-through observed, insufficient outcome data, and not directional.
- Linked signal detail and linked journal note when a note exists.
- Journal prompts when an observed outcome has no linked note.
- Optional pattern reliability, profile diagnostics, confidence calibration, cohort drift, pattern attribution, and digest context panels when those endpoints exist.

The review loop is a learning workflow only. It does not execute trades, connect to brokers, collect account-result metrics, collect order fields, or provide financial advice.

## Journal Workflow

The journal page uses the existing `journal-entries` backend API for notes, edits, archival, and deterministic review against stored outcomes.

The journal captures:

- Decision type: observed, ignored, reviewed, paper followed, external action noted, no action noted, or uncertain.
- User bias: bullish, bearish, neutral, or unclear.
- Notes, tags, optional signal link, optional analysis run link, and optional setup context link.
- Reflection labels returned by the backend: aligned with observed outcome, conflicted with observed outcome, inconclusive, insufficient outcome data, and needs more review.

The form intentionally excludes account-result fields, order fields, margin fields, sizing fields, and broker execution fields. It is not a trade log, not a broker import, and not financial advice.

## Setup Detail View

The setup detail page is for reviewing deterministic setup context around one signal. It is not an execution workflow and does not provide financial advice.

The view shows:

- Header context: symbol, timeframe, directional bias, pattern, confidence, setup quality, latest final candle context when available, and data freshness warnings.
- Setup context: invalidation context, observation zones, target context zones, wait conditions, avoid reasons, timeframe agreement, data-quality warnings, and next observations.
- Evidence and confidence: supporting and conflicting evidence grouped by type, plus confidence components.
- Risk and quality: risk notes, readiness blockers, quality findings, multi-timeframe warnings, and cross-asset context conflicts.
- Outcome history: observed follow-through, observed reversal, no-follow-through, and insufficient-data labels by horizon.
- Historical similar cases: deterministic similarity results with outcome summaries and similarity reasons when available.
- Scenario reasoning and action plan: persisted grounded hypotheses and backend-safe follow-up work, shown read-only.
- Audit and journal: audit timeline summary plus a small journal note form for operator feedback.

Safe language mapping:

- Use `observation zone` for context to monitor.
- Use `invalidation context` for conditions where directional context weakens.
- Use `target context zone` for possible next support, resistance, or range context.
- Use `observed follow-through` and `observed reversal` for outcome labels.
- Use `journal note`, `reviewed`, `observed`, `ignored`, `paper followed`, `external action noted`, `no action noted`, and `uncertain` for feedback.

Journal feedback behavior:

- The page lists existing journal entries for the signal when the journal API is available.
- The form creates a saved journal entry linked to the signal, analysis run, and setup context when those IDs are available.
- The form captures only decision type, title, and journal note.
- The form does not collect account metrics, order fields, margin fields, or broker data.

## Signal Triage Board

The triage board is a frontend composition layer. There is no dedicated backend triage endpoint; the board uses market memory and recent analysis-run signal APIs for candidate discovery, then enriches cards with optional setup context, outcomes, readiness, reports, intelligence quality, latest reasoning, operator reviews, backend action items, and deterministic priority scores when available.

Columns:

- High Quality Context: directional signal, high confidence, acceptable or strong setup context, fresh data, no severe risk, usable readiness, and no critical quality finding.
- Needs Confirmation: medium confidence, wait condition, no outcome context yet, mixed or unknown timeframe agreement, or pending backend follow-up such as outcome evaluation after a horizon.
- Conflicted: quality findings, shadow disagreement, conflicting evidence, cross-asset conflict, reasoning grounding issue, or report-level evidence disagreement.
- Avoid / No Directional Signal: no directional signal, neutral or unclear bias, range/chop context, fakeout risk, below-minimum confidence, or setup-context avoid reasons.
- Stale / Data Issue: stale market memory, missing candle or gap warning, degraded data quality, gap recovery need, stale live subscription, or setup-context data-quality warnings.
- Review Required: blocked readiness, open operator review, low-confidence screenshot review context, blocked reasoning output, or critical quality finding.

The board is read-only and has no drag/drop state. Refresh reloads the current filtered URL. Missing optional enrichment is shown as card-level missing-context badges rather than blocking the card.
When deterministic priority scores are available, cards sort by review priority score first and then fall back to the existing triage column and recency ordering. Missing priority scores do not block the board.

## Data Onboarding Workflow

The onboarding workflow is an operator setup surface for ingestion readiness:

- Select an existing data source or create a minimal source config when the backend allows it.
- Select one or more symbols and supported candle timeframes.
- Run freshness checks for latest final candle time, recent candle count, candle quality, data quality run label, market memory freshness, live subscription status, and provider polling status.
- Create candle gap recovery plans for the checked windows and display gap ranges, expected candle counts, and recovery methods.
- Prepare provider polling request metadata with `createRequests=false`. The workflow does not execute external provider calls.
- Summarize ready symbols, degraded symbols, missing data, stale live feeds, and backend next actions.

Provider keys and paid provider secrets are not entered in the frontend. Source credentials must be configured in backend environment or server-side secret management. The workflow does not create trades, alerts, broker connections, or financial-advice output.

## Watchlist Scanner Controls

The scanner page controls existing backend scan endpoints:

- Create, pause, resume, and archive market watchlists when supported by the backend status field.
- Add symbol/timeframe/source items to watchlists and deactivate items.
- Create watchlist scan configs and single-symbol scan configs with lookback minutes, interval seconds, partial-candle mode, news correlation, AI explanation, reasoning, and action-plan record flags supported by the backend schema.
- Pause, resume, archive, run one config now, list due configs, and run due scan configs.
- Inspect returned scan run counts, scan run items, skipped reasons, error messages, analysis run references, signal result links, confidence, pattern, and data quality component context.

The scanner does not call notification endpoints, execute action items, connect to brokers, require a live provider, or create financial-advice output. Recent scan run history is limited to returned or explicitly selected scan runs because the backend does not currently expose a general list endpoint for scheduled scan runs.

## Safety Language

The UI uses market-intelligence wording such as high quality context, needs confirmation, conflicted, avoid condition, no directional signal, data stale, review required, scheduled scan, watchlist scan, run scan, deterministic analysis, skipped due to insufficient candles, evidence conflict, observed follow-through, observed reversal, setup context, invalidation context, observation zone, journal note, aligned with observed outcome, conflicted with observed outcome, and wait condition. It avoids direct order instructions, certainty claims, broker execution prompts, account-outcome language, financial advice, external notification language for scans, and broker execution.

## Fallback Behavior

The dashboard expects backend modules to be deployed incrementally:

- If market memory is unavailable, watchlists and symbols still render.
- If reports are unavailable, signal pages use signal, evidence, confidence, outcomes, readiness, context, and audit endpoints individually.
- If readiness is unavailable, readiness panels hide behind safe empty states.
- If setup context is unavailable, setup panels show unavailable context without blocking signals.
- If multi-timeframe, cross-asset, quality, reasoning, historical-case, audit, or journal APIs are unavailable, the setup detail page renders scoped empty states and still shows the available setup context.
- If the intelligence report is unavailable, the setup detail page composes from individual optional endpoints.
- If triage enrichment APIs are unavailable, cards remain classified from the signal and market-memory artifacts that did load.
- If signal digests are unavailable, digest panels show an empty state and the rest of the cockpit remains usable.
- If outcome diagnostics, confidence calibration, cohort drift, or pattern attribution endpoints are unavailable, `/review/outcomes` hides those panels and still renders available outcome items.
- If outcomes are unavailable for recent signals, `/review/outcomes` shows an empty queue rather than blocking the page.
- If the journal API is unavailable, `/journal` shows an unavailable state and `/review/outcomes` still shows outcome cards without linked journal notes.
- If the brief cannot reach an optional endpoint, the affected section shows an unavailable or empty state and the rest of `/brief` remains usable.
- If the backend is unreachable, `/brief` shows a top-level backend unavailable state without crashing.
- Journal creation is available on the setup detail page when workspace context is known.
- If scans are unavailable, scan panels render empty states.
- If API or worker health fails, backend state shows the failed fetch without blocking the rest of the UI.
