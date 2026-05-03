# Rolling Market State Memory

Rolling market state memory stores the latest deterministic context snapshot for a workspace,
symbol, optional source, timeframe, and state version. It is a cached market memory layer for
reporting, readiness checks, scans, and future UI surfaces.

It is not a trading signal, financial advice, alerting system, broker workflow, or analysis engine.
It does not call LLMs, run analysis, evaluate outcomes, mutate existing signals, or change candle
storage semantics.

## Purpose

The snapshot answers:

```txt
latest known market state for a symbol/timeframe
latest final candle used
latest data quality status
latest feature, indicator, regime, session, multi-timeframe, and cross-asset summaries
latest signal for the same symbol/timeframe
latest available outcome context
current freshness, stale, degraded, or insufficient-context status
```

Deterministic source artifacts remain authoritative. Market memory stores bounded references and
summaries so downstream modules do not need to repeatedly compose the same latest state.

## Database

Table:

```txt
rolling_market_state_snapshots
```

Identity:

```txt
workspace_id
symbol_id
source_id
timeframe
state_version
```

The identity uses a null-aware unique index, so a `source_id=null` snapshot updates in place instead
of creating duplicate null-source rows.

Labels:

```txt
data_quality_label: strong, acceptable, degraded, poor, insufficient, unknown
freshness_label: fresh, stale, delayed, no_data, unknown
```

## Included Artifacts

The builder reads existing persisted artifacts only:

```txt
latest final candle
latest completed analysis run
latest signal for that analysis when available
latest feature snapshot
latest indicator snapshot
latest advanced feature snapshot
latest market regime context
latest market session context
latest multi-timeframe context
latest cross-asset context
latest signal outcome
latest data quality run
```

No raw full candle series, raw chart images, secrets, provider credentials, prompts, or unbounded
payloads are stored in `context_json`.

## Freshness

Freshness is based on the age of the latest final candle:

```txt
no_data: no final candle exists
fresh: latest final candle age is within the timeframe threshold
delayed: age is greater than the threshold and no more than twice the threshold
stale: age is more than twice the threshold
unknown: unsupported or invalid timing inputs
```

Default thresholds:

```txt
MARKET_MEMORY_FRESH_SECONDS_1M=180
MARKET_MEMORY_FRESH_SECONDS_5M=600
MARKET_MEMORY_FRESH_SECONDS_15M=1800
MARKET_MEMORY_FRESH_SECONDS_1H=7200
```

Other supported timeframes use a conservative fallback of twice the timeframe duration.

## Context And Warnings

`context_json` is bounded and includes compact artifact summaries, ids, timestamps, status labels,
and safety policy metadata.

`warnings_json` records missing artifacts and degraded state such as:

```txt
missing_final_candle
missing_completed_analysis
missing_signal
missing_feature_snapshot
missing_indicator_snapshot
missing_data_quality_run
market_memory_delayed
market_memory_stale
data_quality_degraded
data_quality_insufficient
outcome_insufficient_future_data
```

Warnings are capped by:

```txt
MARKET_MEMORY_MAX_CONTEXT_WARNINGS=50
```

## APIs

Build or refresh one snapshot:

```txt
POST /market-memory/snapshots
```

Request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "sourceId": null,
  "timeframe": "1m",
  "forceRecompute": false
}
```

List snapshots:

```txt
GET /market-memory/snapshots?workspaceId=...&freshnessLabel=fresh
```

Get one cached snapshot by symbol:

```txt
GET /market-memory/snapshots/by-symbol?workspaceId=...&symbolId=...&timeframe=1m&sourceId=...
```

Refresh snapshots for recent final-candle identities in a workspace:

```txt
POST /market-memory/workspaces/{workspace_id}/refresh?limit=500
```

## Idempotency

`POST /market-memory/snapshots` updates the existing row for the same identity and state version.
If the latest candle, analysis, signal, outcome, freshness label, data quality label, context, and
warnings are unchanged, the existing snapshot is returned.

`POST /market-memory/workspaces/{workspace_id}/refresh` derives bounded refresh candidates from
stored final candles and updates each snapshot in place.

## Safety

Market memory does not:

```txt
execute broker actions
auto-trade
send alerts
provide financial advice
call LLMs
classify signals
mutate existing signals
run analysis
evaluate outcomes
override candle storage semantics
store raw full candle series
store raw images
store secrets
```
