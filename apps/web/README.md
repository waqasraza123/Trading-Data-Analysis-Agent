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
- Daily command center start page for a tight morning-to-review workflow.
- API health, worker status, failed fetch states, and last refreshed timestamp.
- Runtime supervisor worker health, stale worker counts, and pending backend run request counts.
- Live data onboarding for source selection, symbol/timeframe readiness, freshness checks, gap planning, and prepare-only recovery metadata.
- Provider health snapshots for source status, candle freshness, missing candles, recent polling failures, gap recovery preparation, and deterministic-analysis readiness.
- Watchlist scanner controls for backend deterministic scan configuration, due scans, run-now execution, scan run item review, and produced signal review.
- Scanner preset gallery for creating watchlists and scheduled scan configs from backend templates without running scans on apply.
- Equity research page for stock universes, deterministic swing scan profiles, ranked swing setup candidates, setup scoring, evidence review, and manual catalyst context.
- Equity data setup panels for provider capability review, mock/CSV universe import, CSV file
  upload, background operation progress, metadata, fundamentals, earnings context, catalyst
  enrichment, and provider request history.
- Guided scanner workflow with hero health metrics, preset gallery, watchlist manager, scan config builder, explicit run-now confirmation, scan history, and generated signal review.
- Guided data onboarding workflow with source, credentials/config, symbols/timeframes, freshness check, gap detection, recovery plan, and ready summary steps.
- In-app notification inbox for reviewing sanitized backend intelligence events, safety status, delivery attempts, and source links.
- Product readiness checklist for explicit daily-use validation across API, database, seed data, workspace setup, data freshness, scanner setup, workers, optional notifications, and journal readiness.
- Guided setup wizard for creating or selecting a workspace, operator, symbols, data source, credential reference, watchlist, scanner preset, preference profile, optional synthetic demo candles, readiness check, and optional explicit first deterministic scan.
- One-click daily workflow control for provider health refresh, recovery planning, deterministic scans, setup context generation, review-priority scoring, digest generation, and brief navigation.
- Daily routine template controls on the command center for named bounded routines such as pre-market scan, session-open reviews, close-of-day review, stale-data repair, quality review, and journal follow-up.
- Personal strategy preference profiles for workspace review filters across markets, symbols, sessions, timeframes, patterns, confidence, setup quality, stale-data tolerance, and confirmation requirements.
- Outcome review and journal loop for turning observed outcomes into daily reflection notes and reliability review.
- Polished daily review surfaces for `/journal`, `/review/outcomes`, `/quality`, and `/notifications` with shared filters, tables, empty states, source links, and safe non-advisory labels.
- Demo mode page at `/demo` for running the backend synthetic product smoke flow and opening the generated command center, brief, triage, scanner, signal detail, and journal artifacts.
- Visual setup chart panels for compact final-candle, zone, signal-window, and observed-outcome context on signal detail pages.
- Command center overview integration for one daily workspace payload, explicit backend-safe quick actions, missing-section fallback, and safe-copy labels.
- First-run onboarding at `/onboarding` with product readiness gate, exact next step guidance, safe setup actions, demo workspace option, command center readiness banner, and workspace selector support.

## Backend Endpoints Used

The client composes data from optional backend APIs:

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /demo-mode/status`
- `POST /demo-mode/run-full-flow`
- `GET /health/workers`
- `GET /runtime-supervisor/health`
- `POST /product-readiness/run`
- `GET /product-readiness/latest`
- `GET /product-readiness/runs`
- `GET /product-readiness/runs/{run_id}`
- `GET /workspaces/{workspace_id}/overview`
- `POST /workspaces/{workspace_id}/quick-actions`
- `GET /onboarding/status`
- `POST /onboarding/actions`
- `GET /workspaces/default-context`
- `GET /workspaces`
- `GET /symbols`
- `GET /symbols/{symbol_id}`
- `GET /market-watchlists`
- `GET /market-watchlists/{watchlist_id}/items`
- `GET /scanner-presets`
- `POST /scanner-presets/seed-default`
- `POST /scanner-presets/{preset_id}/apply`
- `GET /scanner-presets/applications/{application_id}`
- `POST /equity-research/universes`
- `GET /equity-research/universes`
- `GET /equity-research/universes/{universe_id}/members`
- `POST /equity-research/universes/{universe_id}/members`
- `DELETE /equity-research/universes/{universe_id}/members/{member_id}`
- `POST /equity-research/swing-scans`
- `GET /equity-research/swing-scans`
- `GET /equity-research/swing-scans/{scan_run_id}/candidates`
- `GET /equity-research/candidates/{candidate_id}`
- `POST /equity-research/catalysts`
- `GET /equity-research/catalysts`
- `GET /market-memory/snapshots`
- `GET /read-models/symbols`
- `GET /read-models/signals`
- `GET /read-models/command-center`
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
- `GET /analysis-runs/{analysis_run_id}`
- `GET /analysis-runs/{analysis_run_id}/signal`
- `GET /signals/{signal_id}`
- `GET /signals/{signal_id}/priority-score`
- `GET /signals/{signal_id}/outcomes`
- `GET /signals/{signal_id}/setup-context`
- `GET /signals/{signal_id}/advanced-features`
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
- `GET /workspaces/{workspace_id}/daily-brief/latest`
- `GET /daily-briefs`
- `GET /daily-briefs/{brief_id}`
- `GET /daily-briefs/{brief_id}/items`
- `GET /outcomes/performance/patterns`
- `GET /profile-diagnostics/strategy-profiles`
- `GET /profile-diagnostics/patterns`
- `GET /profile-diagnostics/recommendations`
- `GET /confidence-calibration/runs`
- `GET /confidence-calibration/runs/{run_id}/bins`
- `GET /cohort-drift/results/recent`
- `GET /pattern-attribution/runs`
- `GET /pattern-attribution/runs/{run_id}/results`
- `GET /preference-profiles`
- `GET /preference-profiles/default`
- `POST /preference-profiles`
- `PATCH /preference-profiles/{profile_id}`
- `POST /preference-profiles/{profile_id}/archive`
- `POST /preference-profiles/{profile_id}/set-default`
- `GET /preference-profiles/{profile_id}/filter-context`
- `POST /preference-profiles/{profile_id}/match-signal/{signal_id}`
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
- `GET /candles`
- `GET /candles/count`
- `GET /candles/quality`
- `GET /live/subscriptions`
- `GET /provider-polling/requests`
- `GET /provider-health/snapshots`
- `GET /provider-health/workspaces/{workspace_id}/summary`
- `POST /provider-health/workspaces/{workspace_id}/refresh`
- `POST /provider-health/snapshots/{snapshot_id}/prepare-gap-recovery`
- `GET /notification-events`
- `GET /notification-events/{event_id}`
- `POST /notification-events/{event_id}/read`
- `POST /notification-events/{event_id}/acknowledge`
- `POST /notification-events/{event_id}/archive`
- `GET /notification-events/{event_id}/attempts`
- `POST /daily-workflows/run`
- `GET /daily-workflows/runs`
- `GET /daily-workflows/runs/{run_id}`
- `GET /daily-workflows/runs/{run_id}/steps`
- `POST /daily-workflows/runs/{run_id}/cancel`
- `GET /daily-routines/templates`
- `POST /daily-routines/templates/{template_id}/run`
- `GET /daily-routines/runs`
- `GET /daily-routines/runs/{run_id}`
- `GET /daily-routines/runs/{run_id}/steps`
- `POST /data-quality/candle-range/run`
- `POST /candle-gap-recovery/plans`
- `GET /candle-gap-recovery/plans/{plan_id}/items`
- `POST /candle-gap-recovery/plans/{plan_id}/prepare-provider-polling`

Missing optional endpoints render empty states or backend-state warnings instead of crashing the page.
Read model endpoints are preferred where available for triage cards, dashboard symbol state, symbol
detail state, and command center summaries; the existing composed endpoint flow remains the fallback.

## Environment

Create `apps/web/.env.local` when local defaults are not enough:

```sh
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_APP_NAME=Daily Trading Dashboard
NEXT_PUBLIC_AUTH_MODE=dev
NEXT_PUBLIC_AUTH_DEV_USER_ID=
NEXT_PUBLIC_AUTH_DEV_WORKSPACE_ID=
NEXT_PUBLIC_AUTH_BEARER_TOKEN_STORAGE_KEY=
WEB_API_PROXY_BASE_URL=http://127.0.0.1:8000
WEB_API_PROXY_ADMIN_API_KEY=
WEB_API_PROXY_API_KEY_HEADER=x-api-key
WEB_AUTH_SESSION_COOKIE=trading_intelligence_session
```

The API client sends `x-user-id` and `x-workspace-id` in dev mode when those public values are set.
For JWT/mixed deployments, the client can read a bearer token from the configured browser storage
key. Only public frontend configuration belongs in this file. Backend secrets, API keys, database
URLs, and worker credentials must stay in backend environment files.

For the first-party password session flow, set `NEXT_PUBLIC_AUTH_MODE=session` on the web app and
set the API to `AUTH_MODE=session` with a Neon-backed `DATABASE_URL`. The `/login` and `/register`
pages call same-origin Next.js auth handlers, which store the returned backend session token in an
HttpOnly cookie named by `WEB_AUTH_SESSION_COOKIE`.

Browser-initiated `POST`, `PATCH`, and `DELETE` calls go through the same-origin Next.js route
`/api/backend/{path}`. In session mode, browser `GET` calls use the same proxy so the server can
attach the HttpOnly session token. That server-side proxy forwards the request to `WEB_API_PROXY_BASE_URL`
and, when configured, attaches `WEB_API_PROXY_ADMIN_API_KEY` using
`WEB_API_PROXY_API_KEY_HEADER` without exposing the key to browser JavaScript. For local or staging
FastAPI runs with `AUTH_ENABLED=true` and the legacy admin API-key guard, set
`WEB_API_PROXY_ADMIN_API_KEY` to the backend admin key. Production user-facing deployments should
prefer a real session/JWT identity provider; keep the admin-key proxy limited to trusted local or
staging environments.

When building the Docker production image, pass `NEXT_PUBLIC_API_BASE_URL` as a build argument so
browser code points at the public API origin. Pass `WEB_API_PROXY_BASE_URL`,
`WEB_API_PROXY_ADMIN_API_KEY`, and `WEB_API_PROXY_API_KEY_HEADER` as runtime server environment
variables for the standalone Next.js server when mutating web actions must reach an
`AUTH_ENABLED=true` backend through the server-side proxy.

## Run

From `apps/web`:

```sh
npm ci
npm run dev
npm run test:e2e
npm run motion:rollout-audit:report
```

From the repository root:

```sh
./scripts/dev-web.sh
make web-check
```

Run with Docker:

```sh
docker build -f apps/web/Dockerfile -t trading-intelligence-web:latest .
docker compose up --build web
```

The web app uses npm with the committed `package-lock.json`. The production image builds Next.js
standalone output and runs as the non-root `node` user.

Motion governance commands:

```sh
npm run motion:rollout-audit
npm run motion:rollout-audit:json
npm run motion:rollout-audit:strict
npm run motion:rollout-audit:report
node scripts/motion-rollout-audit.mjs --report
```

## E2E Smoke

Playwright smoke tests live under `tests/e2e` and are configured by `playwright.config.ts`.
The harness starts a deterministic local mock API server and points `NEXT_PUBLIC_API_BASE_URL` at
that server, so the smoke suite does not require a running FastAPI process, `DATABASE_URL`,
external providers, LLM credentials, or notification delivery setup.

Run from `apps/web`:

```sh
npm run test:e2e
npm run test:e2e:headed
npm run test:e2e:ui
```

The suite covers first-run onboarding, command-center readiness and overview payloads, safe
quick-action states, core route navigation, optional endpoint fallbacks, and visible safe-copy
checks. Fixture guidance is documented in `docs/e2e-smoke.md`.

Open:

```txt
http://127.0.0.1:3000/command-center
http://127.0.0.1:3000/onboarding
http://127.0.0.1:3000/setup
http://127.0.0.1:3000/readiness
http://127.0.0.1:3000/dashboard
http://127.0.0.1:3000/brief
http://127.0.0.1:3000/scanner
http://127.0.0.1:3000/triage
http://127.0.0.1:3000/notifications
http://127.0.0.1:3000/quality
http://127.0.0.1:3000/review/outcomes
http://127.0.0.1:3000/journal
http://127.0.0.1:3000/preferences/strategy
http://127.0.0.1:3000/data/onboarding
```

Use `?workspaceId=<workspace-id>` to pin a workspace and `?signalId=<signal-id>` to focus a dashboard signal.
Use `/command-center?workspaceId=<workspace-id>` as the default start page for the daily workflow.
Use `/onboarding` to review first-run readiness, complete safe setup actions, create a demo
workspace when demo mode is available, and open the command center when setup is ready.
Use `/setup` to create or select a workspace, configure the first review workflow, optionally seed synthetic demo candles, and then open the command center.
Use `/readiness?workspaceId=<workspace-id>` to run and review the product readiness checklist. The run button is an explicit validation action only; it does not run scans, send alerts, call providers, or execute setup mutations.
Use `/brief?workspaceId=<workspace-id>` to review the current workspace brief.
Use `/scanner?workspaceId=<workspace-id>` to manage watchlists and scheduled scan configs. A returned scan run can be opened with `?runId=<scan-run-id>`, and a daily workflow run can be opened with `?workflowRunId=<workflow-run-id>`.
Use `/triage?workspaceId=<workspace-id>` to review deterministic signals by triage column. Filters support workspace, symbol, timeframe, bias, confidence, triage column, data freshness, profile key, preference profile, only fresh, and only review required.
Use `/review/outcomes?workspaceId=<workspace-id>` to review recent signal outcomes, linked journal notes, and optional diagnostics.
Use `/quality?workspaceId=<workspace-id>` to review the signal quality scoreboard. Filters support workspace, strategy profile, symbol, timeframe, pattern, horizon, and date range.
Use `/journal?workspaceId=<workspace-id>` to create and review reflection notes. Optional `signalId`, `analysisRunId`, `setupContextId`, and `outcomeId` query params prefill context links.
Use `/preferences/strategy?workspaceId=<workspace-id>` to create and maintain review preference profiles. A profile can be selected with `?profileId=<profile-id>`.
Use `/data/onboarding?workspaceId=<workspace-id>` for the data-source onboarding workflow. The page persists selected workspace, source, symbols, and timeframes in the URL and browser storage.

## Modern UI Shell

The integrated product UI uses one Tailwind-native shell from `src/components/layout/AppShell.tsx`.
Desktop navigation is grouped by workflow area, mobile navigation exposes the primary product map,
and all shell links preserve `workspaceId` when a workspace is selected.
Motion polish follows `apps/web/docs/motion-ui.md` (compact/regular/comfortable reveal profiles, route manifest, and rollout checklist).

Shared primitives live under `src/components/ui`, status-specific badges live under
`src/components/status`, and safe labels/formatters/navigation helpers live under `src/lib/ui`.
Feature-specific composition stays local to the page domain, such as command center, brief,
scanner, onboarding, triage, setup review, journal, outcome review, quality, and notifications.

The app should continue to compose backend artifacts through `src/lib/api/client.ts` and typed
domain clients. Optional or not-yet-installed backend endpoints should render loading, empty,
or backend-state warnings instead of breaking routes.

## Scanner Workflow

`/scanner` is a Tailwind-native orchestration surface for deterministic backend scans:

- The hero summarizes configured watchlists, active scan configs, latest selected scan run, failed/skipped counts, source coverage, API status, and worker status.
- Presets cover London open, New York open, crypto 24h, high volatility, trend continuation, reversal risk, range/no directional, needs confirmation, stale data repair, and close-of-day review when backend preset records are available. Applying a preset creates watchlist and/or scan config records only.
- The watchlist manager creates watchlists and active symbol/timeframe items, and can pause, resume, archive, or deactivate records through backend scan APIs.
- The scan config builder supports watchlist and single-symbol scans, lookback, interval, final-candle defaults, and optional news/reasoning/action-plan record toggles when the backend supports them.
- The run-now panel requires an explicit selected config or due-config action and opens the returned scan run for review.
- Scan history and scan run detail show completed, skipped, failed, analysis-run, and signal links when the backend returns them.

The scanner does not connect brokers, place orders, send external messages, or provide financial advice.

## Data Onboarding Workflow

`/data/onboarding` guides source readiness before deterministic analysis:

- Source selection lists configured data sources and supports creating minimal source metadata when the backend permits it.
- Credentials/config review shows configured or missing provider credential references, redacted test status, and server-side configuration guidance. Raw secrets are never shown.
- Symbols/timeframes select final-candle targets for readiness checks.
- Freshness checks read latest final candles, candle counts, candle quality, data quality runs, market memory, live subscriptions, and provider polling status.
- Gap detection creates candle gap recovery plans for selected windows.
- Recovery preparation prepares provider polling metadata with `create_requests=false` from the browser path.
- The ready summary classifies rows as ready for deterministic analysis, degraded, blocked by missing candles, or stale.

The onboarding workflow does not run hidden external calls, execute broker workflows, send alerts, or provide financial advice.

## Routes

- `/dashboard` renders the daily operator cockpit, preferring dashboard symbol read models for current symbol state.
- `/command-center` renders the Daily Trading Command Center start page over existing read-only backend artifacts and command center read models when available.
- `/setup` renders the Guided Workspace Setup Wizard and demo workspace flow.
- `/readiness` renders the Product Readiness Checklist.
- `/scanner` renders watchlist scanner controls for backend deterministic scan orchestration.
- `/triage` renders the read-only signal triage board, preferring signal card read models and falling back to deterministic signal artifact composition.
- `/review/outcomes` renders the outcome and journal review loop over recent signal outcomes.
- `/quality` renders the read-only signal quality scoreboard over stored diagnostics, observed behavior, calibration, validation, drift, attribution, and backtest cohorts.
- `/journal` and `/journal/[entryId]` render reflection note creation, editing, archival, and outcome review when supported by the journal API.
- `/preferences/strategy` renders personal strategy preference profiles for review filtering only.
- `/data/onboarding` renders the live data onboarding and freshness workflow.
- `/brief` renders the workspace daily brief, preferring the backend daily brief endpoint and falling back to web client composition from existing optional backend endpoints.
- `/signals/[signalId]` renders a full read-only setup detail view with a visual setup chart panel, preferring the intelligence report and falling back to individual signal, setup, evidence, confidence, outcome, readiness, context, reasoning, historical-case, quality, audit, and journal APIs when report data is unavailable.
- `/symbols/[symbolId]` renders symbol/timeframe state, preferring dashboard symbol read models and falling back to market memory, recent signals, outcomes, scheduled scans, and analysis runs.

## Daily Workflow Loop

The integrated web surface is arranged for a deterministic daily review loop:

1. Verify data freshness in `/data/onboarding` or the command center freshness panel.
2. Use `/setup` when you need to create or configure the first workspace workflow, then use `/readiness` for explicit daily-use validation.
3. Use “Run daily scan” in `/command-center` or `/scanner` to refresh status, prepare recovery plans, run deterministic scans, generate setup context, score review priority, and generate digest/brief context.
4. Use scanner presets in `/scanner` when a repeatable session, watchlist, or data-repair scan configuration is useful.
5. Read `/brief` for the persisted backend daily brief, with frontend composition as fallback.
6. Triage stored signals in `/triage`, optionally scoped by a preference profile.
7. Inspect setup context in `/signals/[signalId]`.
8. Add or update observational journal notes in `/journal`.
9. Review observed outcomes in `/review/outcomes`.
10. Review in-app notification events in `/notifications` and diagnostic warnings in `/quality`.
11. Revisit summaries in `/command-center`, `/dashboard`, `/brief`, or symbol detail.

The “Run daily scan” control does not execute notifications, broker actions, or external provider polling by default. It shows completed, skipped, and failed workflow steps and links to produced brief, scan run, and signal records.

The shared navigation links Command Center, Readiness, Brief, Scanner, Triage, Quality, Notifications, Data, Journal, and Preferences. Workspace-aware links preserve `workspaceId` where the source page knows it. Stale-data and data-quality sections link back to onboarding; readiness blockers link to their owning setup surfaces; scan-result and triage cards link to setup detail; outcome cards link to journal prompts; symbol pages link back into scanner and onboarding; command center links to notification events and the quality scoreboard.

The merged workflow contract is documented in `docs/daily-use-workflow.md`.

## Polished Review Surfaces

The daily review pages share a compact Tailwind review-surface system for consistent headers, metrics, filters, tables, cards, and empty states. These pages are optimized for fast operator review over stored backend artifacts; they do not create broker workflows, account-result records, external delivery triggers, or financial advice.

## Notification Inbox

The notification inbox at `/notifications` is an in-app review surface over sanitized
`notification_events`. It lists supported intelligence events, filters by inbox state, severity,
event type, delivery state, and source type, shows safe payload summaries, redaction warnings,
delivery attempts, and source links for signals, outcomes, digests, provider health, data quality,
action items, scans, gap recovery, and journal entries.

Supported event types are signal classification, review recommendation, outcome evaluation,
digest creation, data-quality degradation, stale market memory, due reasoning action, blocked
readiness, opened operator review, completed scan, degraded provider health, and needed gap
recovery. The UI uses safe language such as Review needed, Data stale, Scan completed, Outcome
ready, Setup context available, Provider degraded, and Gap recovery needed. It is an in-app review
surface only and does not trigger realtime notifications.

## Daily Trading Command Center

The command center is the default premium daily cockpit at `/command-center`. It is a frontend composition layer in `apps/web/src/lib/api/commandCenter.ts` and `apps/web/src/lib/command-center/composeCommandCenter.ts`. It uses the backend daily brief through the shared brief client when a persisted brief is available, then falls back to the existing provider health, signal priority, preference profile, triage, scanner, journal, market memory, digest, outcome, readiness, review, action item, product readiness, provider polling, and health clients.

Sections:

- Hero/status band: workspace, session time, data readiness, last refresh, backend health, and quick links for refresh, scanner, triage, data onboarding, and an explicit deterministic daily scan.
- Review First: dense setup table with bias, symbol/timeframe, confidence, priority label, setup quality, freshness, main reason, and setup detail links.
- Needs Confirmation: compact strip for mixed context, pending final-candle or outcome context, pending data recovery, and medium-confidence review states.
- Avoid Conditions: stale data, no directional signal, conflicting evidence, low quality, range/chop/fakeout context, and unresolved review conditions.
- Data Reliability: fresh/stale counts, provider health, gap recovery needs, provider polling status, and data onboarding links.
- Outcome Review: observed continuation, observed reversal, and no-follow-through outcomes linked back to setup detail.
- Workflow Progress: latest daily workflow run, completed/skipped/failed steps, and links to brief, scanner, and triage.
- Notifications / Review Items: unread inbox count, review-required items, blocked readiness, pending backend-safe actions, and readiness/inbox links.

The command center keeps all copy non-advisory. It is not a broker terminal, not an auto-trading page, and not financial advice. It does not call broker APIs, create broker instructions, send external notifications, or execute action items.

## Daily Brief

`/brief` is the structured narrative summary for the daily cockpit. It prefers `GET /workspaces/{workspace_id}/daily-brief/latest` for persisted backend briefs and falls back to frontend composition when that endpoint is missing or has no usable brief. The fallback reads existing optional endpoints for market memory, signal digests, setup context, outcomes, readiness, operator reviews, action items, scheduled scans, watchlists, API health, and workers.

The brief header shows the period, generated time, workspace/watchlist context, source path, and summary stats. Sections cover what changed, fresh symbols, review-first setups, needs confirmation, avoid conditions, outcomes ready, watch next, pending backend-safe actions, and data quality/recovery context. Empty states distinguish no workspace, no brief generated, no fresh data, no setups, and backend unavailable.

The brief uses safe market-intelligence wording only. It is not a trading execution surface and does not provide financial advice.

## Outcome Review Loop

The outcome review page is a frontend composition layer in `apps/web/src/lib/api/outcomeReview.ts`. It does not add a backend endpoint. Because the backend exposes outcomes by signal and analysis run rather than a workspace-wide outcome queue, the page loads recent analysis runs, resolves their deterministic signals, loads each signal's outcomes, and links any matching journal entries.

The page shows:

- A polished queue table of recent observed outcomes by signal, horizon, outcome label, pattern, bias, linked setup context, and reflection status.
- Outcome labels using safe review language: observed continuation, observed reversal, no follow-through observed, insufficient outcome data, and not directional.
- Linked signal detail and linked journal note when a note exists.
- Journal prompts when an observed outcome has no linked note.
- Optional pattern reliability, profile diagnostics, confidence calibration, cohort drift, pattern attribution, and digest context panels when those endpoints exist.

The review loop is a learning workflow only. It does not execute trades, connect to brokers, collect account-result metrics, collect order fields, or provide financial advice.

## Signal Quality Scoreboard

The quality page is a frontend composition layer in `apps/web/src/lib/api/quality.ts` and `apps/web/src/lib/quality/composeQualityScoreboard.ts`. It does not add a backend endpoint. It composes existing read-only backend endpoints into one analytics dashboard for deterministic signal quality and historical behavior.

The page adds a “what to review” section above the diagnostics so sample-size warnings, drift findings, calibration warnings, and profile review recommendations are visible before deeper tables.

Backend inputs:

- `/outcomes/performance/strategy-profiles`, `/outcomes/performance/patterns`, and `/outcomes/performance/symbols` for observed continuation, reversal, no-follow-through, and sample-size metrics.
- `/profile-diagnostics/strategy-profiles`, `/profile-diagnostics/patterns`, and `/profile-diagnostics/recommendations` for profile and pattern review labels.
- `/confidence-calibration/runs` and `/confidence-calibration/runs/{runId}/bins` for confidence alignment.
- `/walk-forward-validations/runs`, `/walk-forward-validations/runs/{runId}/windows`, and `/walk-forward-validations/runs/{runId}/comparisons` for stability windows.
- `/cohort-drift/results/recent` for baseline versus recent cohort behavior.
- `/pattern-attribution/runs` and `/pattern-attribution/runs/{runId}/results` for selected, rejected, and blocking pattern behavior.
- `/backtest-experiments/runs` and `/backtest-experiments/runs/{runId}/cohorts` for optional cohort context.
- `/workspaces`, `/symbols`, and `/strategy-profiles` for filters and labels.

Safe metrics include continuation rate, reversal rate, no follow-through rate, confidence alignment, observed behavior, sample size, review recommended, degraded, drift detected, and data coverage. The page avoids account-result, broker, and advice language. It does not run diagnostics automatically; if diagnostics have not been created, it shows empty states and run-diagnostics-first suggestions.

## Journal Workflow

The journal page uses the existing `journal-entries` backend API for notes, edits, archival, and deterministic review against stored outcomes. It now adds workspace, decision type, status, symbol, timeframe, and signal filters. Symbol/timeframe filters apply when journal entries have analysis-run context available.

The journal captures:

- Decision type: observed, ignored, reviewed, paper followed, external action noted, no action noted, or uncertain.
- User bias: bullish, bearish, neutral, or unclear.
- Notes, tags, optional signal link, optional analysis run link, and optional setup context link.
- Reflection labels returned by the backend: aligned with observed outcome, conflicted with observed outcome, inconclusive, insufficient outcome data, and needs more review.

The form intentionally excludes account-result fields, order fields, margin fields, sizing fields, and broker execution fields. It is not a trade log, not a broker import, and not financial advice.

## Setup Detail View

The setup detail page is for reviewing deterministic setup context around one signal. It is not an execution workflow and does not provide financial advice.

The redesigned `/signals/[signalId]` route uses feature-local setup review components under
`src/components/setup-review/` and presentation helpers under `src/lib/setup-review/`. It keeps the
existing `setupDetail` composition contract behind `src/lib/api/setupReview.ts` so optional backend
modules can remain independently deployable.

The view shows:

- Sticky setup header: symbol, timeframe, directional bias, confidence, review priority context, setup quality, data freshness, evidence counts, and links to audit, report/reasoning, and journal sections.
- Visual setup chart: recent final candles, latest final candle marker, signal window, observation zones, invalidation context, target context zones, support/resistance context when available, review marker, setup quality/freshness/data-quality badges, warnings, and observed outcome markers.
- Setup context: invalidation context, observation zones, target context zones, wait conditions, avoid reasons, timeframe agreement, data-quality warnings, and next observations.
- Evidence and confidence: supporting and conflicting evidence grouped by type, plus confidence components.
- Risk and quality: risk notes, readiness blockers, quality findings, multi-timeframe context, and cross-asset context conflicts.
- Wait / avoid: wait conditions, avoid reasons, unresolved observations, stale-data warnings, and degraded-data context.
- Historical context: deterministic similar cases, recent observed outcomes by horizon, and profile/pattern behavior when backend summaries are available.
- Scenario reasoning and action plan: persisted grounded hypotheses and backend-safe follow-up work, shown read-only.
- Audit and journal: audit timeline summary plus a small journal note form for operator feedback.

Safe language mapping:

- Use `observation zone` for context to monitor.
- Use `invalidation context` for conditions where directional context weakens.
- Use `target context zone` for possible next support, resistance, or range context.
- Use `observed follow-through` and `observed reversal` for outcome labels.
- Use `journal note`, `reviewed`, `observed`, `ignored`, `paper followed`, `external action noted`, `no action noted`, and `uncertain` for feedback.

Visual setup chart behavior:

- The chart uses reusable SVG components under `apps/web/src/components/charts/` and utility functions under `apps/web/src/lib/charts/`.
- It uses final candles from `GET /candles`; partial candles are not requested.
- It uses the analysis run window when available and pads that window to provide nearby context.
- It inserts bounded visual gaps when final-candle timestamps indicate missing expected intervals.
- It uses existing setup-context zones and optional advanced-feature support/resistance context.
- It renders empty and warning states when candles, zones, or optional backend modules are unavailable.
- Additional detail is documented in `apps/web/docs/visual-setup-charts.md`.

Journal feedback behavior:

- The page lists existing journal entries for the signal when the journal API is available.
- The form creates a saved journal entry linked to the signal, analysis run, and setup context when those IDs are available.
- The form captures only decision type, title, and journal note.
- The form does not collect account metrics, order fields, margin fields, or broker data.

## Signal Triage Board

The triage board is a frontend composition layer. There is no dedicated backend triage endpoint; the board uses market memory and recent analysis-run signal APIs for candidate discovery, then enriches cards with optional setup context, outcomes, readiness, reports, intelligence quality, latest reasoning, operator reviews, backend action items, and deterministic priority scores when available.

Columns:

- Review First: directional setup, higher confidence, acceptable or strong setup context, fresh data, stronger review-priority score, usable readiness, and no critical quality finding.
- Needs Confirmation: medium confidence, wait condition, no outcome context yet, mixed or unknown timeframe agreement, or pending backend follow-up such as outcome evaluation after a horizon.
- Conflicted: quality findings, shadow disagreement, conflicting evidence, cross-asset conflict, reasoning grounding issue, or report-level evidence disagreement.
- Avoid / No Directional: no directional signal, neutral or unclear bias, range/chop context, fakeout risk, below-minimum confidence, or setup-context avoid reasons.
- Stale / Data Issue: stale market memory, missing candle or gap warning, degraded data quality, gap recovery need, stale live subscription, or setup-context data-quality warnings.
- Review Required: blocked readiness, open operator review, low-confidence screenshot review context, blocked reasoning output, or critical quality finding.

The board is read-only and has no drag/drop state. Sticky filters support workspace, preference profile, symbol search, symbol, timeframe, bias, confidence, bucket, freshness, profile key, only-fresh, review-required, and sort mode. Refresh reloads the current filtered URL. Missing optional enrichment is shown as card-level missing-context badges rather than blocking the card.
When deterministic priority scores are available, cards sort by review priority score first and then fall back to the existing triage column and recency ordering. Missing priority scores do not block the board.
Cards show symbol/timeframe, bias, confidence, priority score, setup quality, freshness, data quality, top reason, top risk note, evidence/conflict/outcome counts, and an outcome badge when available. Card links open `/signals/[signalId]` for setup review only.

## Data Onboarding Workflow

The onboarding workflow is an operator setup surface for ingestion readiness:

- Select an existing data source or create a minimal source config when the backend allows it.
- Select one or more symbols and supported candle timeframes.
- Run freshness checks for latest final candle time, recent candle count, candle quality, data quality run label, market memory freshness, live subscription status, and provider polling status.
- Create candle gap recovery plans for the checked windows and display gap ranges, expected candle counts, and recovery methods.
- Prepare provider polling request metadata with `createRequests=false`. The workflow does not execute external provider calls.
- Refresh provider health snapshots when the backend supports them and review source status, symbol/timeframe freshness, missing candles, polling failures, and recovery preparation.
- Summarize ready symbols, degraded symbols, missing data, stale live feeds, and backend next actions.

Provider keys and paid provider secrets are not entered in the frontend. Source credentials must be configured in backend environment or server-side secret management. The workflow does not create trades, alerts, broker connections, or financial-advice output.
When `/provider-credentials` is available, onboarding shows whether a source has a configured
credential reference and can trigger a backend-safe configuration test. The UI still does not accept
raw secrets; operators must configure `secret_ref` values server-side or through a future secure
secret-manager flow.

## Watchlist Scanner Controls

The scanner page controls existing backend scan endpoints:

- Seed and apply backend scanner presets for London open, New York open, crypto 24h, high volatility, trend continuation, reversal risk, range/no directional signal, needs confirmation, stale data repair, and close-of-day review workflows.
- Create, pause, resume, and archive market watchlists when supported by the backend status field.
- Add symbol/timeframe/source items to watchlists and deactivate items.
- Create watchlist scan configs and single-symbol scan configs with lookback minutes, interval seconds, partial-candle mode, news correlation, AI explanation, reasoning, and action-plan record flags supported by the backend schema.
- Pause, resume, archive, run one config now, list due configs, and run due scan configs.
- Inspect returned scan run counts, scan run items, skipped reasons, error messages, analysis run references, signal result links, confidence, pattern, and data quality component context.

Preset apply creates watchlists and scan configs only. It does not run scans; run-now remains a separate explicit control. The scanner does not call notification endpoints, execute action items, connect to brokers, require a live provider, or create financial-advice output. Recent scan run history is limited to returned or explicitly selected scan runs because the backend does not currently expose a general list endpoint for scheduled scan runs.

## Safety Language

The UI uses market-intelligence wording such as high quality context, needs confirmation, conflicted, avoid condition, no directional signal, data stale, review required, scheduled scan, watchlist scan, run scan, deterministic analysis, skipped due to insufficient candles, evidence conflict, observed follow-through, observed reversal, setup context, invalidation context, observation zone, journal note, aligned with observed outcome, conflicted with observed outcome, and wait condition. It avoids direct order instructions, certainty claims, broker execution prompts, account-outcome language, financial advice, external notification language for scans, and broker execution.

## Frontend Design System

Shared interface primitives live under `src/components/ui`:

- `Surface`, `Card`, `Section`, `SectionHeader`, `PageHeader`, and `PageContainer` define the daily cockpit frame, spacing, route headings, and panel rhythm.
- `MetricCard`, `StatGrid`, `Badge`, `StatusPill`, and status wrappers under `src/components/status` normalize dense dashboard metrics and bias, confidence, freshness, data quality, setup quality, outcome, readiness, priority, and worker labels.
- `EmptyState`, `ErrorState`, `LoadingState`, and `Skeleton` keep missing endpoint, failed endpoint, and loading surfaces visually consistent.
- `Button`, `Tabs`, `FilterBar`, `ActionBar`, `Timeline`, `Tooltip`, and `Divider` cover common interactions used by filters, refresh links, workflow steps, and traceability views.

The app shell lives under `src/components/layout`:

- `AppShell` wraps route content in the responsive cockpit frame.
- `Sidebar` renders grouped desktop navigation with active route state.
- `Topbar` renders workspace context and a safe `/health` API status indicator.
- `MobileNav` renders compact mobile navigation from the same registry.
- `WorkspaceSwitcher` and `PageContainer` provide shared context and content bounds.
- Motion primitives for route and panel animation are documented in `docs/motion-ui.md`.

Shared UI helpers live under `src/lib/ui`:

- `navigation.ts` is the source of truth for daily cockpit navigation.
- `labels.ts`, `safeLabels.ts`, and `safeCopy.ts` centralize safe display labels and replacement wording.
- `statusStyles.ts` maps backend status values into the shared badge tones.
- `cn.ts` and `formatters.ts` provide local class composition and formatting re-exports.

The shell and workflow links use the same route registry and highlight the active section. Page headers should describe read-only review context, show workspace and last-updated metadata when available, and avoid advisory language. More detailed guidance is in `docs/design-system.md`.

## Fallback Behavior

The dashboard expects backend modules to be deployed incrementally:

- If market memory is unavailable, watchlists and symbols still render.
- If reports are unavailable, signal pages use signal, evidence, confidence, outcomes, readiness, context, and audit endpoints individually.
- If readiness is unavailable, readiness panels hide behind safe empty states.
- If setup context is unavailable, setup panels show unavailable context without blocking signals.
- If chart candle data is unavailable, the setup detail page shows the rest of the setup context and a scoped visual chart warning.
- If multi-timeframe, cross-asset, quality, reasoning, historical-case, audit, or journal APIs are unavailable, the setup detail page renders scoped empty states and still shows the available setup context.
- If the intelligence report is unavailable, the setup detail page composes from individual optional endpoints.
- If triage enrichment APIs are unavailable, cards remain classified from the signal and market-memory artifacts that did load.
- If signal digests are unavailable, digest panels show an empty state and the rest of the cockpit remains usable.
- If outcome diagnostics, confidence calibration, cohort drift, or pattern attribution endpoints are unavailable, `/review/outcomes` hides those panels and still renders available outcome items.
- If quality scoreboard endpoints are unavailable, `/quality` records scoped API failures, renders available sections, and shows empty states with run-diagnostics-first suggestions when no stored diagnostics are available.
- If outcomes are unavailable for recent signals, `/review/outcomes` shows an empty queue rather than blocking the page.
- If the journal API is unavailable, `/journal` shows an unavailable state and `/review/outcomes` still shows outcome cards without linked journal notes.
- If the brief cannot reach an optional endpoint, the affected section shows an unavailable or empty state and the rest of `/brief` remains usable.
- If the backend is unreachable, `/brief` shows a top-level backend unavailable state without crashing.
- Journal creation is available on the setup detail page when workspace context is known.
- If scans are unavailable, scan panels render empty states.
- If API or worker health fails, backend state shows the failed fetch without blocking the rest of the UI.
