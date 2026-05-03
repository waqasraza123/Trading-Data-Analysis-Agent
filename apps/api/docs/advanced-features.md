# Advanced Price Action Features

The advanced price action feature pack is a deterministic backend-only layer that persists extra
market context for future pattern detection, regime context, historical cases, quality gates,
reports, and reasoning modules.

It does not classify final signals, mutate signals, update pattern candidates, execute broker
actions, send alerts, or provide financial advice. Deterministic final candles remain the source of
truth.

## Snapshot

Advanced feature snapshots are stored in `advanced_feature_snapshots`.

One snapshot is unique per:

```txt
analysis_run_id + feature_pack_version
```

The default version is:

```txt
ADVANCED_FEATURE_PACK_VERSION=v1
```

## Computed Groups

- `impulseJson`: impulse direction, large body count, consecutive direction count, average body to
  range ratio, and impulse score.
- `correctionJson`: pullback count, average pullback depth, whether pullbacks were against the
  primary movement direction, and correction score.
- `wickPressureJson`: upper/lower wick pressure scores, rejection direction, and large wick counts.
- `movementEfficiencyJson`: net move, gross movement, efficiency score, and efficient/moderate/choppy
  label.
- `compressionExpansionJson`: compression and expansion flags, ranges, expansion ratio, and label.
- `swingStructureJson`: swing highs/lows, higher/lower swing counts, and structure label.
- `supportResistanceJson`: recent support and resistance zones, nearest zones, and zone confidence.
- `exhaustionJson`: body expansion with wick rejection, decreasing body sequence, exhaustion
  direction, and exhaustion score.
- `liquiditySweepJson`: sweep above recent high, sweep below recent low, failed hold after sweep,
  sweep direction, and sweep score.
- `warningsJson`: non-fatal calculation warnings.

## Configuration

```txt
ADVANCED_FEATURE_PACK_VERSION=v1
ADVANCED_FEATURE_MIN_CANDLE_COUNT=20
ADVANCED_FEATURE_SWING_LOOKBACK=3
ADVANCED_FEATURE_ZONE_LOOKBACK=80
ADVANCED_FEATURE_COMPRESSION_LOOKBACK=20
ADVANCED_FEATURE_EXPANSION_MULTIPLIER=1.5
ADVANCED_FEATURE_WICK_PRESSURE_THRESHOLD=0.55
ADVANCED_FEATURE_MOVEMENT_EFFICIENCY_THRESHOLD=0.60
```

## API

Generate or reuse an analysis-run snapshot:

```txt
POST /analysis-runs/{analysis_run_id}/advanced-features
POST /analysis-runs/{analysis_run_id}/advanced-features?forceRecompute=true
```

Read an analysis-run snapshot:

```txt
GET /analysis-runs/{analysis_run_id}/advanced-features
```

Generate or reuse through a persisted signal:

```txt
POST /signals/{signal_id}/advanced-features
POST /signals/{signal_id}/advanced-features?forceRecompute=true
```

Read through a persisted signal:

```txt
GET /signals/{signal_id}/advanced-features
```

## Limitations

- The pack uses final candles only and does not include partial candles.
- It is not a trading signal by itself.
- It does not use LLM classification.
- It does not alter existing signal classification behavior.
- It does not auto-run inside the analysis lifecycle in this phase.
- It uses safe context terms such as impulse, correction, wick pressure, rejection, compression,
  expansion, swing structure, support zone, resistance zone, movement efficiency, exhaustion risk,
  and liquidity sweep candidate.

## Future Use

Future modules can consume this persisted context for pattern profiles, market-regime context,
historical case matching, quality gates, intelligence reports, and grounded reasoning. Those modules
should treat the snapshot as deterministic evidence and continue to avoid broker execution,
auto-trading, copy trading, alerts, and financial advice.

When combined with reproducibility manifests, event studies, confidence calibration, and webhook
outbox events, the advanced feature snapshot remains context only. It should not be used to mutate a
final signal, change a strategy profile automatically, claim causation, or create a delivery alert.
