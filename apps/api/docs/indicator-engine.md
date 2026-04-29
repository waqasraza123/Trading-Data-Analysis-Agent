# Indicator Snapshots

This slice adds deterministic indicator calculation and persistence. Pattern detection is implemented in the next engine layer; indicators still do not classify final signals by themselves.

## Boundary

Indicator calculation runs after feature snapshots are persisted:

```txt
analysis run
-> candle preflight
-> feature snapshot
-> deterministic indicator engine
-> indicator_snapshots row
-> indicators_calculated audit log
-> pattern candidate engine
```

Indicators are supporting evidence for future pattern and signal logic. They do not override price-action features and do not classify the market by themselves.

## Database

New table:

```txt
indicator_snapshots
```

Fields:

```txt
id
analysis_run_id
workspace_id
symbol_id
timeframe
indicators_json
created_at
```

Indexes:

```txt
analysis_run_id
workspace_id + symbol_id + timeframe
```

Migration:

```txt
alembic/versions/202604290930_indicator_snapshots.py
```

## Modules

```txt
app/modules/indicators/
  atr.py
  ema.py
  engine.py
  macd.py
  models.py
  repository.py
  rsi.py
  schemas.py
  serialization.py
  service.py
```

## Implemented Indicators

### EMA

Periods:

```txt
EMA 9
EMA 21
EMA 50
```

State:

```txt
bullish_alignment
bearish_alignment
mixed
unknown
```

`unknown` means there were not enough warmup plus analysis candles to calculate every EMA.

### RSI

Period:

```txt
RSI 14
```

State:

```txt
oversold
bearish_momentum
neutral
bullish_momentum
overbought
unknown
```

### MACD

Configuration:

```txt
EMA 12
EMA 26
signal EMA 9
```

State:

```txt
bullish
bearish
neutral
unknown
```

### ATR

Period:

```txt
ATR 14
```

ATR state compares current ATR to baseline ATR:

```txt
compressed
normal
expanding
spike
unknown
```

`unknown` means current or baseline ATR could not be calculated.

## Readiness

Every indicator group includes `isReady`.

The top-level calculation block includes:

```txt
analysisCandleCount
warmupCandleCount
baselineCandleCount
inputCandleCount
isReady
```

`isReady=false` is not a failure. It makes missing warmup or baseline data explicit so future confidence scoring can reduce confidence instead of guessing.

## API

Indicator snapshots are available through:

```txt
GET /analysis-runs/{analysis_run_id}/indicators
```

This returns the latest indicator snapshot for the analysis run.

## Analysis Lifecycle Integration

Current successful run behavior:

```txt
queued
-> running
-> candles_loaded
-> analysis_windows_resolved
-> features_calculated
-> indicators_calculated
-> completed
```

In the current lifecycle, `completed` means deterministic feature snapshots, indicator snapshots, and pattern candidates were calculated and stored. Later phases continue from these artifacts into signal classification, evidence, confidence, risk notes, and explanations.

## Serialization

Indicator values are stored in JSONB. Decimal values are serialized as strings to preserve market precision.

## Not Implemented In This Slice

```txt
signals
signal evidence
confidence components
risk notes
deterministic explanations
LLM explanations
news correlation
indicator tests or golden datasets
```
