# Pattern Candidates

This slice adds deterministic rule-based pattern detection and persistence. It does not add final signal classification, confidence scoring, signal evidence tables, explanations, news correlation, broker behavior, or LLM calls.

## Boundary

Pattern detection runs after feature and indicator snapshots are persisted:

```txt
analysis run
-> candle preflight
-> feature snapshot
-> indicator snapshot
-> deterministic pattern engine
-> pattern_candidates rows
-> patterns_detected audit log
```

Pattern candidates are not final signals. They are structured candidates that later signal classification can rank, resolve, and explain.

## Database

New table:

```txt
pattern_candidates
```

Fields:

```txt
id
analysis_run_id
workspace_id
symbol_id
pattern_type
bias
strength_score
is_selected
evidence_json
risk_notes_json
metrics_json
created_at
```

Indexes:

```txt
analysis_run_id
workspace_id + symbol_id + pattern_type
analysis_run_id + is_selected
```

Migration:

```txt
alembic/versions/202604291000_pattern_candidates.py
```

## Modules

```txt
app/modules/patterns/
  bearish_breakdown.py
  bullish_breakout.py
  chop.py
  common.py
  continuation.py
  engine.py
  fakeout.py
  models.py
  repository.py
  reversal.py
  schemas.py
  serialization.py
  service.py
```

## Implemented Detectors

### Bullish Breakout

Checks:

```txt
latest close above previous range high
at least two consecutive closes above previous range high
volatility is normal or expanding
higher lows outnumber lower lows
latest candle has bullish body strength
```

### Bearish Breakdown

Checks:

```txt
latest close below previous range low
at least two consecutive closes below previous range low
volatility is normal or expanding
lower highs outnumber higher highs
latest candle has bearish body strength
```

### Bullish Continuation

Checks:

```txt
trend state is short_term_uptrend
EMA alignment is bullish_alignment
higher-low structure remains intact
latest candle resumes upward movement
movement efficiency is not choppy
```

### Bearish Continuation

Checks:

```txt
trend state is short_term_downtrend
EMA alignment is bearish_alignment
lower-high structure remains intact
latest candle resumes downward movement
movement efficiency is not choppy
```

### Bullish Reversal

Checks:

```txt
first half of the analysis window moved bearish
latest candle rejects previous range low
latest candle has a large lower wick
latest candle follows through higher
RSI has recovered above the neutral-recovery threshold
```

### Bearish Reversal

Checks:

```txt
first half of the analysis window moved bullish
latest candle rejects previous range high
latest candle has a large upper wick
latest candle follows through lower
RSI has weakened below the neutral-weakness threshold
```

### Fakeout

Checks:

```txt
previous range boundary was breached
latest close returned inside the previous range
latest candle has a large wick
follow-through reversed after the breach
baseline range is available
```

### Sideways Range

Checks:

```txt
latest close remains inside the previous range
movement efficiency is low
trend structure is mixed_or_sideways
ATR state is compressed or normal
direction changes are frequent
```

### Low-Volatility Chop

Checks:

```txt
average candle bodies are small relative to range
ATR state is compressed
movement efficiency is very low
direction changes are frequent
there is no clean breakout
```

## Strength Scoring

Each detector emits weighted evidence items. `strength_score` is the weighted pass ratio from `0.0000` to `1.0000`.

The strongest candidate is marked `is_selected=true` only when its score is at least:

```txt
0.3500
```

If every candidate is weak, all candidates remain unselected. This avoids forcing bullish or bearish output in unclear markets.

## Evidence, Risk Notes, And Metrics

Each candidate stores:

```txt
evidence_json
risk_notes_json
metrics_json
```

Evidence items include the rule name, pass/fail state, observed value, threshold, and weight.

Risk notes currently flag:

```txt
missing baseline range
incomplete indicator readiness
shallow analysis windows
```

Metrics capture detector-specific inputs such as previous range levels, wick ratios, trend counts, movement efficiency, and direction changes.

## API

Pattern candidates are available through:

```txt
GET /analysis-runs/{analysis_run_id}/patterns
```

The response is ordered with the selected candidate first, then by strength score descending.

## Retry Behavior

Retrying an analysis run recalculates pattern candidates and replaces that run's previous candidate rows. This keeps one current candidate set per analysis run until a future analysis-attempt model exists.

## Analysis Lifecycle Integration

Current successful run behavior:

```txt
queued
-> running
-> candles_loaded
-> analysis_windows_resolved
-> features_calculated
-> indicators_calculated
-> patterns_detected
-> completed
```

In this phase, `completed` means deterministic feature snapshots, indicator snapshots, and pattern candidates were calculated and stored. Later phases continue into signal classification, evidence, confidence, risk notes, and explanations.

## Serialization

Pattern evidence and metrics are stored in JSONB. Decimal market values are serialized as strings to preserve precision.

## Not Implemented In This Slice

```txt
final signal classification
signal evidence records
confidence components
signal risk notes
deterministic explanations
LLM explanations
news correlation
pattern tests or golden datasets
```
