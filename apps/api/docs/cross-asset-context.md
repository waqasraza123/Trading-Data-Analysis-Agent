# Cross-Asset Context

Cross-asset context is a deterministic backend-only intelligence layer that compares stored final
candles across related symbols for the same analysis window.

It stores contextual correlation, co-movement, divergence, and lead/lag observations. It does not
infer causation, classify signals, mutate existing signals, provide financial advice, send alerts,
call LLMs, execute broker actions, or provide directional instructions.

## Purpose

The module can answer contextual questions such as:

```txt
Did two symbols move together during the same window?
Did one symbol show a stronger lead/lag relationship by a few candles?
Was the base symbol moving against compared symbols?
Did a signal occur while related symbols were aligned, mixed, isolated, or conflicting?
```

The stored results are intended for future reports, decision-readiness diagnostics, historical case
comparison, and operator review.

## Tables

`cross_asset_context_runs` stores one requested context build:

```txt
workspace_id
analysis_run_id nullable
signal_id nullable
base_symbol_id
timeframe
source_id nullable
context_version
status
start_time
end_time
compared_symbol_count
result_count
summary
metadata_json
created_at
updated_at
```

`cross_asset_context_results` stores one base/compared symbol pair per run:

```txt
workspace_id
context_run_id
base_symbol_id
compared_symbol_id
timeframe
start_time
end_time
base_move
compared_move
base_direction
compared_direction
correlation_score
alignment_label
lead_lag_offset_candles
lead_lag_label
divergence_score
data_quality_label
metadata_json
created_at
```

## Calculation Rules

- Uses final candles only.
- Partial candles are ignored.
- Candles are aligned by timestamp for same-window correlation.
- Per-candle movement is normalized as `(close - open) / open`.
- Total window movement is normalized from the first candle open to the last candle close.
- Correlation is a deterministic Pearson-style score from `-1.00000` to `1.00000`.
- Directional alignment compares per-candle movement signs.
- Divergence increases when candles often move in opposite directions or correlation is negative.
- Lead/lag checks offsets from `-CROSS_ASSET_LEAD_LAG_MAX_OFFSET` to
  `+CROSS_ASSET_LEAD_LAG_MAX_OFFSET` and selects the strongest deterministic relationship.
- Missing or sparse candles degrade to `insufficient_data`.

Lead/lag offset semantics:

```txt
positive offset = base symbol leads compared symbol
negative offset = compared symbol leads base symbol
zero offset = synchronous relationship
null offset = no clear or insufficient relationship
```

## Labels

Run statuses:

```txt
pending
completed
completed_with_warnings
failed
```

Alignment labels:

```txt
aligned
partially_aligned
conflicting
divergent
insufficient_data
```

Lead/lag labels:

```txt
base_leads
compared_leads
synchronous
no_clear_relationship
insufficient_data
```

Data quality labels:

```txt
strong
acceptable
degraded
insufficient_data
```

## APIs

Build context for an analysis run:

```http
POST /analysis-runs/{analysis_run_id}/cross-asset-context
Content-Type: application/json

{
  "comparedSymbolIds": ["00000000-0000-0000-0000-000000000000"],
  "forceRecompute": false
}
```

Read latest analysis-run context:

```txt
GET /analysis-runs/{analysis_run_id}/cross-asset-context
```

Build context for a signal:

```http
POST /signals/{signal_id}/cross-asset-context
Content-Type: application/json

{
  "comparedSymbolIds": ["00000000-0000-0000-0000-000000000000"],
  "forceRecompute": false
}
```

Read latest signal context:

```txt
GET /signals/{signal_id}/cross-asset-context
```

List pair results:

```txt
GET /cross-asset-context/runs/{run_id}/results
GET /cross-asset-context/runs/{run_id}/results?limit=100&offset=0
```

## Settings

```txt
CROSS_ASSET_CONTEXT_VERSION=v1
CROSS_ASSET_MIN_CANDLES=20
CROSS_ASSET_MAX_COMPARED_SYMBOLS=20
CROSS_ASSET_LEAD_LAG_MAX_OFFSET=5
CROSS_ASSET_ALIGNMENT_THRESHOLD=0.60
CROSS_ASSET_DIVERGENCE_THRESHOLD=0.60
```

## Safety Boundary

Cross-asset context is contextual intelligence only. It may say that related symbols showed
correlation, co-movement, divergence, lead/lag, cross-asset confirmation, or cross-asset conflict.
It must not claim causation, promise movement, provide directional instructions, create alerts, or
change deterministic signal classification.

## Future Integration

Future report and reasoning layers may read persisted cross-asset context as a cited artifact. They
should treat it as supporting context only and preserve the same no-causation, no-advice, no-signal
mutation boundary.
