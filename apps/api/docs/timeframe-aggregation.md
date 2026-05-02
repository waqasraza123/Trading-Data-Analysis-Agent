# Multi-Timeframe Candle Aggregation

This backend module derives higher-timeframe candles from existing final lower-timeframe candles and
stores deterministic multi-timeframe context for analysis runs and signals.

It does not classify new signals, modify stored final signals, create alerts, provide financial
advice, or perform broker execution.

## Aggregation Rules

- Only final base candles are eligible.
- Partial candles are ignored.
- Missing base candles are not synthesized.
- A derived candle is complete only when every expected base candle exists.
- Incomplete windows are recorded in the aggregation run metadata and skipped.
- Incomplete candles are not stored in the main `candles` table.
- Derived candles are stored through the existing candle validation and storage path.
- Existing final candle conflict protection remains active.

Supported pairs:

```txt
1m -> 5m
1m -> 15m
1m -> 30m
1m -> 1h
5m -> 15m
5m -> 30m
5m -> 1h
15m -> 1h
1h -> 4h
```

## Derived Candle Values

For each complete target window:

```txt
open = first base candle open
high = max base candle high
low = min base candle low
close = last base candle close
volume = sum base volume when every base candle has volume, otherwise null
```

Target timestamps are aligned to UTC target timeframe boundaries.

## Completeness Policy

`TIMEFRAME_AGGREGATION_MIN_COMPLETENESS` defaults to `1.0`. With the default policy, only fully
complete windows are persisted as derived candles. Runs store:

- expected base candle count
- available base candle count
- produced candle count
- skipped candle count
- incomplete window count
- a capped list of incomplete window metadata

## Lineage

Each produced derived candle gets a `derived_candle_lineage` row with:

- aggregation run id
- derived candle id
- base and target timeframes
- derived timestamp
- base window bounds
- expected and actual base counts
- completeness score

Derived candles use an internal `derived_aggregation` data source so provider-original candles remain
distinguishable from aggregation output.

## Multi-Timeframe Context

Context can be built for an analysis run or signal. The service:

1. Loads the analysis run or signal.
2. Resolves the primary timeframe.
3. Reads higher-timeframe final candles.
4. Calculates deterministic trend direction, range behavior, volatility behavior, and latest candle
   direction from higher-timeframe candles.
5. Compares persisted signal bias, when available, against higher-timeframe trend context.
6. Stores alignment labels, an agreement score, a summary, structured context JSON, and warnings.

No existing signal classification is changed.

## API Examples

Create an aggregation run:

```http
POST /timeframe-aggregation/runs
Content-Type: application/json

{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "sourceId": null,
  "baseTimeframe": "1m",
  "targetTimeframe": "15m",
  "startTime": "2026-05-02T00:00:00Z",
  "endTime": "2026-05-02T03:59:00Z"
}
```

Read aggregation results:

```txt
GET /timeframe-aggregation/runs/{run_id}
GET /timeframe-aggregation/runs
GET /timeframe-aggregation/derived-candles/{candle_id}/lineage
```

Build context:

```http
POST /analysis-runs/{analysis_run_id}/multi-timeframe-context
Content-Type: application/json

{
  "contextTimeframes": ["15m", "1h"],
  "forceRecompute": false
}
```

Signal context uses the same request body:

```txt
POST /signals/{signal_id}/multi-timeframe-context
GET /analysis-runs/{analysis_run_id}/multi-timeframe-context
GET /signals/{signal_id}/multi-timeframe-context
```

## Settings

```txt
TIMEFRAME_AGGREGATION_VERSION=v1
TIMEFRAME_AGGREGATION_MIN_COMPLETENESS=1.0
TIMEFRAME_AGGREGATION_ALLOWED_TARGETS=5m,15m,30m,1h,4h
MULTI_TIMEFRAME_CONTEXT_VERSION=v1
```

## Scheduled Scan Integration

Scheduled scans can call the aggregation service before analysis or reporting so higher-timeframe
context is available for diagnostics. That integration is intentionally separate from this module and
should preserve the same final-candle-only and no-signal-mutation rules.
