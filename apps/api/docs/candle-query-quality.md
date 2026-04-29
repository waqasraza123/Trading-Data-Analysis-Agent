# Candle Query And Quality APIs

This slice exposes the read layer that future analysis runs will use. It does not start analysis, calculate indicators, detect patterns, classify signals, or generate explanations.

## Purpose

The backend now has a clean candle read boundary:

```txt
candles table
-> candle repository
-> candle service
-> candle API routes
-> future analysis lifecycle
```

The read layer works the same for historical CSV/JSON candles and live-originated candles because both paths store rows in the same `candles` table.

## Implemented APIs

```txt
GET /candles
GET /candles/count
GET /candles/quality
GET /candles/latest
```

All endpoints require:

```txt
workspace_id
symbol_id
timeframe
```

Windowed endpoints also require:

```txt
start_time
end_time
```

Optional filters:

```txt
source_id
is_final
limit
offset
```

## Final And Partial Candle Policy

Default read behavior uses final candles only:

```txt
is_final=true
```

Partial live candles can be queried explicitly:

```txt
is_final=false
```

The quality endpoint reads both final and partial candles internally so it can report partial availability, but the quality score is based on final candles.

Future analysis code must continue using final candles by default and include partial live candles only when explicitly requested by an analysis mode.

## GET /candles

Returns ordered candle rows for a window.

Example:

```txt
GET /candles?workspace_id=...&symbol_id=...&timeframe=1m&start_time=2026-04-29T09:00:00Z&end_time=2026-04-29T10:00:00Z
```

Default response includes final candles only.

## GET /candles/count

Returns the count for the same candle window and filters.

Example response:

```json
{
  "count": 60
}
```

## GET /candles/quality

Returns completeness and partial-candle visibility for a window.

Example response:

```json
{
  "expectedCandles": 60,
  "availableFinalCandles": 58,
  "availablePartialCandles": 1,
  "missingCandles": 2,
  "duplicateCandles": 0,
  "qualityScore": "0.96667",
  "hasPartialLatestCandle": true
}
```

Quality rules:

```txt
expected candles are derived from timeframe, start_time, and end_time
available final candles count toward quality_score
partial candles are reported but do not improve quality_score
missing candles are expected timestamps without a final candle
duplicate candles are detected from duplicate timestamps in the queried set
```

The current database uniqueness constraint prevents duplicate rows for the same workspace, symbol, source, timeframe, and timestamp. Duplicate reporting remains useful when future query modes combine sources or when ingestion diagnostics pass unsaved series into the quality helper.

## GET /candles/latest

Returns the latest candle for a symbol/timeframe, optionally scoped to a source and final/partial state.

Default response returns the latest final candle.

Use:

```txt
is_final=false
```

to inspect the latest partial candle.

## Service Methods For Future Analysis

`CandleService` now exposes:

```txt
list_candles
count_candles
get_latest_candle
calculate_window_quality
fetch_candle_window
fetch_warmup_window
fetch_baseline_window
```

The future analysis lifecycle should call these service methods instead of querying SQLAlchemy models directly.

## Validation

The service validates:

```txt
start_time must be before end_time
symbol must exist
source must exist when source_id is supplied
source must belong to the requested workspace
timestamps are normalized to UTC before querying
```

## Not Implemented In This Slice

```txt
analysis run creation
insufficient-data status transitions
feature calculations
indicator calculations
pattern detection
signal classification
LLM explanations
news correlation
scheduled live scanner
UI
```
