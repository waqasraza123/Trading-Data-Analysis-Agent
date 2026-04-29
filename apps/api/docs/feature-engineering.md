# Feature Engineering Snapshots

This slice adds deterministic feature calculation and persistence. It does not add indicators, pattern detection, signal classification, evidence, confidence, risk notes, explanations, news correlation, or LLM calls.

## Boundary

Feature calculation runs after analysis lifecycle candle preflight succeeds:

```txt
analysis run
-> candle window loaded
-> quality checked
-> warmup/baseline windows loaded
-> deterministic feature engine
-> feature_snapshots row
-> features_calculated audit log
```

The feature engine receives stored candles only. It does not call external APIs and does not ask an LLM to classify market behavior.

## Database

New table:

```txt
feature_snapshots
```

Fields:

```txt
id
analysis_run_id
workspace_id
symbol_id
timeframe
start_time
end_time
features_json
created_at
```

Indexes:

```txt
analysis_run_id
workspace_id + symbol_id + timeframe
start_time + end_time
```

Migration:

```txt
alembic/versions/202604290900_feature_snapshots.py
```

## Modules

```txt
app/modules/features/
  candle_shape.py
  engine.py
  models.py
  movement.py
  range.py
  repository.py
  schemas.py
  serialization.py
  service.py
  trend.py
  volatility.py
```

## Feature Groups

### Movement

Calculated from the first open and last close in the analysis window:

```txt
startPrice
endPrice
absoluteMove
percentageMove
pipsMoved
ticksMoved
netDirection
totalCandleMovement
movementEfficiency
```

Pip movement is only present when the symbol has `pip_size`.

Tick movement is only present when the symbol has `tick_size`.

### Candle Shape

Calculated from candle bodies, wicks, and ranges:

```txt
averageBodySize
averageUpperWick
averageLowerWick
bodyToRangeRatio
upperWickRatio
lowerWickRatio
largeBodyCount
largeWickCount
indecisionCount
rejectionCount
```

### Range

Current range uses the analysis window. Previous range uses the baseline window.

```txt
previousRangeHigh
previousRangeLow
currentRangeHigh
currentRangeLow
candlesClosedAbovePreviousRange
candlesClosedBelowPreviousRange
distanceFromRangeHigh
distanceFromRangeLow
rangeState
```

If no baseline candles exist, previous range fields are null and `rangeState` is `no_baseline_range`.

### Volatility

Uses analysis, warmup, and baseline candles:

```txt
trueRange
currentAverageRange
baselineAverageRange
atr
baselineAtr
atrExpansionRatio
volatilityState
largeCandleCount
```

Volatility states:

```txt
unknown
compressed
normal
expanding
spike
```

### Trend

Uses adjacent highs/lows and net slope:

```txt
higherHighsCount
higherLowsCount
lowerHighsCount
lowerLowsCount
trendSlope
trendState
```

Trend states:

```txt
short_term_uptrend
short_term_downtrend
mixed_or_sideways
```

### Data Quality

The candle quality report is copied into `features_json.dataQuality` so feature snapshots remain auditable against the input completeness at calculation time.

## API

Feature snapshots are available through:

```txt
GET /analysis-runs/{analysis_run_id}/features
```

This returns the latest feature snapshot for the analysis run.

## Analysis Lifecycle Integration

`AnalysisService.process_preflight` now persists a feature snapshot after candle sufficiency passes.

Current successful run behavior:

```txt
queued
-> running
-> candles_loaded
-> analysis_windows_resolved
-> features_calculated
-> completed
```

In this phase, `completed` means deterministic features were calculated and stored. Later phases will continue from the stored feature snapshot into indicators, patterns, signals, evidence, confidence, and explanations.

## Data Sufficiency

Feature snapshots are not created when:

```txt
analysis window has zero candles
expected candle count is zero
required final candles are missing
duplicate candle timestamps are present in the analysis query result
```

Live-window runs may include the current partial candle only when `include_partial_live_candle=true`.

## Serialization

Feature values are stored in JSONB. Decimal values are serialized as strings to preserve market precision.

## Not Implemented In This Slice

```txt
indicator snapshots
pattern candidates
signals
signal evidence
confidence components
risk notes
deterministic explanations
LLM explanations
news correlation
feature tests or golden datasets
```
