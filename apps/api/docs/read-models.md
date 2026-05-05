# Dashboard Read Models

Read models materialize compact dashboard snapshots from existing persisted artifacts. They are optimized for cockpit reads and are rebuildable at any time from source-of-truth tables.

## Purpose

- Return triage signal cards without fetching each signal, setup context, readiness, priority, outcome, quality, and report endpoint separately.
- Return current symbol state for dashboard and symbol detail views from one indexed table.
- Return command center summary sections from one read payload.
- Keep stale, freshness, data-quality, priority, setup-quality, readiness, and warning status in one response.

## Source Of Truth

The source of truth remains the underlying deterministic artifacts: signals, market memory, signal priority, setup context, outcomes, action items, provider health, data quality, decision readiness, market regime/session context, daily briefs, and reports. Read model rows are snapshots only.

Read model rebuilds do not:

- Run analysis or scans.
- Reclassify signals.
- Evaluate outcomes.
- Mutate source artifacts.
- Call LLMs or external providers.
- Send notifications.
- Execute broker workflows, auto-trading, or financial-advice flows.

## Tables

- `dashboard_symbol_read_models`
- `signal_card_read_models`
- `command_center_read_models`

`dashboard_symbol_read_models` is unique by workspace, symbol, nullable source, timeframe, and read model version. `signal_card_read_models` is unique by signal and read model version. Command center rows are append-only generated snapshots ordered by `generated_at`.

## Settings

- `READ_MODEL_VERSION`, default `v1`
- `READ_MODEL_DEFAULT_LIMIT`, default `200`
- `READ_MODEL_MAX_LIMIT`, default `1000`

## Rebuild APIs

```txt
POST /read-models/symbols/rebuild
GET /read-models/symbols
POST /read-models/signals/{signal_id}/rebuild
POST /read-models/signals/rebuild-workspace
GET /read-models/signals
POST /read-models/command-center/rebuild
GET /read-models/command-center
```

Symbol rebuild request:

```json
{
  "workspaceId": "workspace-uuid",
  "symbolId": "symbol-uuid",
  "sourceId": null,
  "timeframe": "5m"
}
```

Workspace signal card rebuild request:

```json
{
  "workspaceId": "workspace-uuid",
  "limit": 500
}
```

Command center rebuild request:

```json
{
  "workspaceId": "workspace-uuid",
  "periodStart": null,
  "periodEnd": null
}
```

## Frontend Fallback

The web app prefers read model endpoints for triage cards, dashboard symbol state, symbol detail state, and command center quality summary context. If a read model endpoint is missing, empty, or unavailable, the existing frontend composition remains the fallback path.

## Operational Notes

Read models should be refreshed by explicit rebuild endpoints or future workflow steps after source artifacts change. They are safe to delete and rebuild because they do not own source data.
