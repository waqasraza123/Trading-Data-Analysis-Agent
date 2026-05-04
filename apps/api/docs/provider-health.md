# Provider Health Snapshots

Provider health snapshots make provider polling, candle freshness, missing-candle detection, data
quality, live subscription state, market memory, and gap recovery planning visible in one
operational workflow.

The module is data reliability only. It does not fetch external providers, mutate candles, execute
broker actions, auto-trade, send alerts, or provide financial advice.

## Storage

Provider health persists:

```txt
provider_health_snapshots
```

Each snapshot records workspace, source, provider, optional symbol/timeframe scope, status,
freshness label, latest final candle, latest successful and failed provider polling timestamps,
latest gap recovery plan, latest data quality run, consecutive failures, missing candles, stale
seconds, summary, and metadata.

Status values:

```txt
healthy
degraded
stale
failing
unavailable
unknown
```

Freshness labels:

```txt
fresh
delayed
stale
no_data
unknown
```

## Freshness Thresholds

Defaults:

```txt
PROVIDER_HEALTH_VERSION=v1
PROVIDER_HEALTH_FRESH_SECONDS_1M=180
PROVIDER_HEALTH_FRESH_SECONDS_5M=600
PROVIDER_HEALTH_FRESH_SECONDS_15M=1800
PROVIDER_HEALTH_FRESH_SECONDS_1H=7200
PROVIDER_HEALTH_MAX_FAILURES_DEGRADED=2
PROVIDER_HEALTH_MAX_FAILURES_FAILING=5
```

Other repository timeframes fall back to two timeframe durations.

## Behavior

`build_health_snapshot` reads existing persisted state only:

- `data_sources`
- final candles
- provider polling requests and errors
- candle gap recovery plans
- data quality runs
- live feed subscriptions
- market memory snapshots
- watchlist items when refreshing workspace health

It does not call provider adapters and does not create provider polling requests.

`build_workspace_health` creates source-level snapshots and symbol/timeframe snapshots discovered
from candles, live subscriptions, active watchlist items, and sources.

`prepare-gap-recovery` is explicit. It creates or reuses a candle gap recovery plan for the
snapshot window, then delegates to the existing recovery preparation workflow. By default it returns
prepare-only provider polling metadata. It creates pending polling request rows only when
`createRequests=true`.

The web workflow uses provider health snapshots in `/command-center` and `/data/onboarding` to
show data fresh, data stale, missing candles, provider degraded, polling failed, recovery plan
needed, and ready for deterministic analysis states.

## API

```txt
POST /provider-health/snapshots
GET /provider-health/snapshots
GET /provider-health/workspaces/{workspace_id}/summary
POST /provider-health/workspaces/{workspace_id}/refresh
POST /provider-health/snapshots/{snapshot_id}/prepare-gap-recovery
```

Build snapshot:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "timeframe": "1m",
  "forceRecompute": true
}
```

Prepare gap recovery:

```json
{
  "createRequests": false
}
```

## Safety Boundary

Provider health is read aggregation plus explicit recovery preparation. It does not:

- call external providers;
- mutate candle data;
- run analysis;
- execute broker, order, or position workflows;
- auto-trade;
- send alerts;
- provide financial advice.
