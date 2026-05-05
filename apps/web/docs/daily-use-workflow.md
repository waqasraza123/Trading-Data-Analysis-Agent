# Daily Use Workflow

The daily-use workflow ties the daily brief, one-click workflow runner, scanner presets, quality
scoreboard, and notification inbox into one operator loop:

```txt
data freshness -> run workflow -> scanner presets -> brief -> triage -> setup detail -> journal/outcome review
```

## Route Surface

- `/command-center`: daily start page with backend daily brief context, daily workflow controls,
  scanner state, quality warnings, notification event counts, review-first setups, and next
  backend-safe actions.
- `/brief`: persisted backend daily brief first, frontend composition fallback second.
- `/scanner`: scanner preset gallery, watchlists, scan configs, explicit scan controls, and daily
  workflow status.
- `/triage`: read-only review-priority board over stored signal context.
- `/quality`: observed behavior, calibration, validation, drift, attribution, and data coverage.
- `/notifications`: in-app intelligence event review state, not external delivery by default.
- `/signals/[signalId]`: setup detail with visual chart context.
- `/journal` and `/review/outcomes`: reflection notes and observed outcome review.

## Backend Contracts

- Daily briefs use `GET /workspaces/{workspace_id}/daily-brief/latest` and
  `GET /daily-briefs/{brief_id}/items`.
- Daily workflows use `POST /daily-workflows/run`, `GET /daily-workflows/runs`, and
  `GET /daily-workflows/runs/{run_id}/steps`.
- Scanner presets use `GET /scanner-presets`, `POST /scanner-presets/seed-default`, and
  `POST /scanner-presets/{preset_id}/apply`.
- Quality scoreboard data is composed from existing outcome, diagnostic, calibration,
  validation, drift, attribution, backtest, symbol, workspace, and strategy profile endpoints.
- Notification inbox uses `GET /notification-events`,
  `POST /notification-events/{event_id}/read`,
  `POST /notification-events/{event_id}/acknowledge`,
  `POST /notification-events/{event_id}/archive`, and delivery-attempt reads.

## Safety Contract

The workflow is market intelligence only.

- Daily workflows execute deterministic backend work only.
- Scanner preset application creates watchlist and scan config records only.
- Notification events are in-app intelligence events unless external delivery is explicitly
  configured and invoked on the backend.
- Quality scoreboard metrics describe observed behavior, sample size, confidence alignment,
  continuation, reversal, and no-follow-through context only.
- Existing deterministic artifacts remain the source of truth.
- UI language must stay review-oriented: review first, setup context, invalidation context,
  observation zone, target context zone, data ready for deterministic analysis, review priority,
  observed follow-through, observed reversal, notification event, and scan completed.

The workflow does not place orders, call brokers, run hidden scans, execute external delivery by
default, auto-trade, copy-trade, or provide financial advice.
