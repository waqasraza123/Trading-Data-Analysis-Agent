# Intelligence Metrics

The intelligence metrics registry exposes internal backend counters for operational and product
intelligence. These metrics describe artifact production, safety states, review queues, quality
signals, and backend work health.

They are not trading metrics. They do not claim strategy performance, broker profit and loss,
investment quality, win rate, expected return, or financial advice.

## Purpose

The registry answers backend questions such as:

- How many analyses were created, completed, or failed.
- How many signals exist by classification status and bias.
- How many outcomes exist by outcome label.
- How many reasoning runs were blocked, used fallback, or failed grounding.
- How many reasoning action items are pending, due, or failed.
- How many data quality records or import errors exist.
- How many chart screenshot runs require review.
- How many provider polling or live feed requests failed.
- What the current backend intelligence health summary is.

## Collection Behavior

Collection is database-backed and does not use an external observability provider. The collector
checks whether each source table and column exists before querying it.

When a module table is missing, collection continues and records a structured warning with
`code=metrics_table_missing`. When a specific column is missing, collection records
`code=metrics_column_missing` and continues with the remaining counters.

Snapshots can be persisted in `intelligence_metric_snapshots` for later operational review.

## Counter Sources

Available counters are collected from these source tables when present:

```txt
analysis_runs
signals
signal_outcomes
llm_reasoning_runs
reasoning_action_items
market_scan_runs
strategy_profile_diagnostic_runs
strategy_profile_diagnostics
pattern_outcome_diagnostics
calibration_recommendations
data_quality_findings
import_batches
import_errors
operator_reviews
chart_screenshot_runs
provider_polling_requests
live_feed_events
webhook_outbox_events
webhook_outbox
notification_messages
notification_worker_runs
ai_intelligence_runs
```

Optional module tables can be absent without failing the metrics response.

## Health Summary

`operationalHealth` is a compact internal summary derived from counters. It can report:

```txt
healthy
partial
attention
degraded
failed
```

`partial` means collection completed with missing optional modules or columns. `attention` means
review, due-work, quality, or reasoning counters need operator attention. `degraded` means failed
operational work exists.

This health summary is an operational backend signal only. It is not market analysis and should not
be shown as trading quality.

## APIs

```txt
GET /intelligence-metrics/workspace/{workspace_id}
GET /intelligence-metrics/global
POST /intelligence-metrics/snapshots/workspace/{workspace_id}
POST /intelligence-metrics/snapshots/global
GET /intelligence-metrics/snapshots/latest
GET /intelligence-metrics/snapshots
```

`GET /intelligence-metrics/workspace/{workspace_id}` returns live counters scoped to one workspace.

`GET /intelligence-metrics/global` returns live counters across all workspaces.

`POST /intelligence-metrics/snapshots/workspace/{workspace_id}` collects workspace counters and
persists a snapshot.

`POST /intelligence-metrics/snapshots/global` collects global counters and persists a snapshot.

`GET /intelligence-metrics/snapshots/latest` accepts optional `workspace_id` and `snapshot_type`
query parameters.

`GET /intelligence-metrics/snapshots` accepts optional `workspace_id`, `snapshot_type`, `status`,
`limit`, and `offset` query parameters.

## Snapshot Table

`intelligence_metric_snapshots` stores:

```txt
id
workspace_id
snapshot_type
status
collected_at
metrics_json
warnings_json
created_at
```

Supported `snapshot_type` values:

```txt
workspace
global
module
operational_health
```

Supported `status` values:

```txt
completed
completed_with_warnings
failed
```
