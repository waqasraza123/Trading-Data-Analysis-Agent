# Daily Routine Templates

Daily routines compose existing backend-safe workflows into reusable operator templates. They are deterministic orchestration records, not broker execution, auto-trading, order placement, alerts, or financial-advice workflows.

## Tables

- `daily_routine_templates`: active or archived routine templates with explicit bounded steps, default filters, schedule hints, and safety metadata.
- `daily_routine_runs`: one persisted execution record per template run with request input, artifact IDs, step summaries, status, and error summary.
- `daily_routine_run_steps`: one persisted record per step with input, output, skip reason, error message, and timing.

## Seeded Templates

- `pre_market_scan`
- `london_open_review`
- `new_york_open_review`
- `crypto_24h_review`
- `close_of_day_review`
- `stale_data_repair`
- `outcome_review`
- `quality_review`
- `journal_follow_up`

Templates are global by default with `workspace_id = null`. Workspace-specific templates can be added later using the same schema.

## Safe Steps

Supported step keys:

- `provider_health_refresh`
- `gap_recovery_prepare`
- `daily_workflow_run`
- `scheduled_scan_run`
- `setup_context_generate`
- `signal_priority_score`
- `market_memory_refresh`
- `digest_generate`
- `brief_generate`
- `outcome_review_collect`
- `quality_summary_collect`
- `journal_follow_up_collect`
- `notification_event_create`

Collect steps read existing persisted artifacts only. Gap recovery prepares plans and optional provider-polling request rows only when both request input and settings allow it. Notification steps only create backend notification event rows when explicitly enabled and do not deliver external notifications.

## Settings

- `DAILY_ROUTINE_VERSION`, default `v1`
- `DAILY_ROUTINE_MAX_STEPS`, default `20`
- `DAILY_ROUTINE_ENABLE_NOTIFICATIONS`, default `false`

## APIs

- `POST /daily-routines/seed-default`
- `GET /daily-routines/templates`
- `GET /daily-routines/templates/{template_id}`
- `POST /daily-routines/templates/{template_id}/run`
- `GET /daily-routines/runs`
- `GET /daily-routines/runs/{run_id}`
- `GET /daily-routines/runs/{run_id}/steps`

Run request:

```json
{
  "workspaceId": "uuid",
  "watchlistId": "uuid-or-null",
  "preferenceProfileId": "uuid-or-null",
  "enableNotifications": false,
  "allowProviderPolling": false,
  "force": false,
  "inputJson": {}
}
```

## Safety

Routine runs are explicit and bounded by template steps plus `DAILY_ROUTINE_MAX_STEPS`. The runner does not place orders, call brokers, execute trading actions, auto-trade, copy-trade, or suggest directional actions. External notifications remain disabled by default.
