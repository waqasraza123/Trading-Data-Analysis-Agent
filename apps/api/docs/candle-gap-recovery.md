# Real-Time Candle Gap Recovery Planner

The candle gap recovery planner records missing final-candle ranges and recovery metadata. It is
planning and orchestration only.

It does not fetch provider data automatically, mutate candles directly, execute trades, connect to
brokers, send alerts, provide UI behavior, or produce financial advice.

## Module Layout

```txt
app/modules/candle_gap_recovery/
  models.py
  schemas.py
  repository.py
  detector.py
  service.py
  routes.py
```

## Storage

The planner persists two tables:

```txt
candle_gap_recovery_plans
candle_gap_recovery_items
```

Plans store the workspace, symbol, optional source, timeframe, detection window, recovery version,
aggregate request counts, summary, status, and metadata.

Items store each grouped missing final-candle range, expected candle count, recovery method, status,
optional linked `provider_polling_requests.id`, skip/error details, and metadata.

Plan statuses:

```txt
draft
ready
completed
completed_with_warnings
failed
cancelled
```

Item statuses:

```txt
planned
queued
completed
skipped
failed
cancelled
```

Recovery methods:

```txt
provider_polling
manual_import
unavailable
```

## Gap Detection

Detection uses final candles only. Partial live candles do not satisfy a missing final candle.

The detector:

- normalizes request timestamps to UTC
- requires `startTime` and `endTime` to align with the requested timeframe
- rejects windows larger than `CANDLE_GAP_RECOVERY_MAX_RANGE_DAYS`
- builds expected candle timestamps from `startTime` through `endTime`
- compares expected timestamps to stored final candle timestamps
- groups adjacent missing timestamps into gap ranges
- caps retained grouped ranges at `CANDLE_GAP_RECOVERY_MAX_GAPS`

With `sourceId=null`, the planner checks the symbol/timeframe across all sources. With a concrete
`sourceId`, it checks only that source.

## Recovery Planning

`create_recovery_plan` creates a durable plan and one item per retained gap. It does not update
`candles`.

Every detected gap is marked as an analysis-quality blocker and a potential scheduled-scan blocker
because analysis and scheduled scans use complete final-candle windows by default. The existing
analysis and scheduled-scan exception for one latest partial candle remains owned by those modules;
this planner still records the missing final candle.

Provider polling is selected only when:

- `sourceId` is set
- the source belongs to the workspace
- the source is active
- `source_type=api_polling`
- the provider is supported by the existing provider polling adapter registry
- the gap fits within `PROVIDER_POLLING_MAX_CANDLES_PER_REQUEST`

Provider symbol resolution uses:

1. `data_sources.config_json.providerSymbol`
2. `data_sources.config_json.provider_symbol`
3. `symbols.symbol`

When provider polling is not eligible, items remain planned for `manual_import` or `unavailable`
with a skip reason in item metadata.

## Provider Polling Integration

`prepare_provider_polling_requests(planId, createRequests=false)` returns provider polling payload
metadata for eligible items only. It does not call provider adapters and does not fetch external
data.

When `createRequests=true`, the service creates pending `provider_polling_requests` rows directly
and links them to recovery items. It does not call `ProviderPollingService.create_request` because
that service immediately executes the provider fetch.

Created polling rows use:

```txt
status = pending
request_metadata_json.createdBy = candle_gap_recovery
request_metadata_json.doesNotExecutePolling = true
```

A later execution phase may run those pending provider polling requests through the existing
provider polling ingestion path.

## Settings

```txt
CANDLE_GAP_RECOVERY_VERSION=v1
CANDLE_GAP_RECOVERY_MAX_GAPS=500
CANDLE_GAP_RECOVERY_MAX_RANGE_DAYS=30
```

## API

```txt
POST /candle-gap-recovery/plans
GET /candle-gap-recovery/plans/{plan_id}
GET /candle-gap-recovery/plans/{plan_id}/items
POST /candle-gap-recovery/plans/{plan_id}/prepare-provider-polling
POST /candle-gap-recovery/plans/{plan_id}/cancel
```

Create plan:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "sourceId": null,
  "timeframe": "1m",
  "startTime": "2026-05-03T10:00:00Z",
  "endTime": "2026-05-03T11:00:00Z"
}
```

Prepare provider polling without creating request rows:

```json
{
  "createRequests": false
}
```

Prepare provider polling and create pending request rows:

```json
{
  "createRequests": true
}
```

## Not Implemented

- automatic provider fetch execution
- candle mutation outside existing ingestion/polling paths
- provider polling request execution or worker changes
- completion reconciliation from later imported candles
- broker execution
- auto-trading
- alerts
- UI
- financial advice
