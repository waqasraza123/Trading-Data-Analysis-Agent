# Signal Outcome Evaluation

Signal outcome evaluation adds a historical behavior loop after deterministic signal classification. It answers what happened in final candle data after a persisted signal without changing the signal, overriding the deterministic classifier, or producing broker execution output.

This is not broker accounting, an account-return calculator, financial advice, or automatic trading. The API uses outcome language: continuation, follow-through, reversal, favorable movement, adverse movement, and observed historical behavior.

## Evaluation Flow

Signals and outcomes are separate artifacts.

- Signals record what the deterministic classifier concluded at analysis time.
- Outcomes record what later final candle data showed after that classification.
- Replay signals receive their own outcomes; original signal outcomes are not mutated.
- Chart screenshot decisions that triggered analysis are evaluated through the linked analysis run and persisted signal.

## Horizons

Default horizons are configured by `OUTCOME_DEFAULT_HORIZONS_MINUTES` and default to:

```txt
5,15,30,60
```

Each signal can have one outcome per horizon and `OUTCOME_EVALUATION_VERSION`. The current default evaluation version is `v1`.

## Reference Price

The evaluator uses the best deterministic reference price available:

1. An explicit signal reference price if a future signal model adds one.
2. The last final candle close at or before `analysis_run.end_time`.
3. If no final reference candle exists, the outcome is marked failed with stable metadata.

Outcome evaluation uses final candles only.

## Calculation Rules

For bullish signals:

- favorable movement = future highest high - reference price
- adverse movement = reference price - future lowest low
- net movement = final future close - reference price

For bearish signals:

- favorable movement = reference price - future lowest low
- adverse movement = future highest high - reference price
- net movement = reference price - final future close

Directional labels are deterministic:

- `continuation`
- `partial_follow_through`
- `no_follow_through`
- `reversal`
- `insufficient_data`

Neutral, unclear, no-signal, or insufficient-evidence classifications are not forced into directional results. They are marked `not_directional` or `sideways_after_signal`, and `directionFollowed` remains null.

Forex outcomes use `symbol.pip_size` for pip conversion. Crypto outcomes use `symbol.tick_size` for tick conversion. Missing pip/tick metadata leaves converted fields null and records a metadata warning.

## APIs

```txt
POST /signals/{signal_id}/outcomes/evaluate
GET /signals/{signal_id}/outcomes
GET /signals/{signal_id}/outcomes/{horizon_minutes}
POST /analysis-runs/{analysis_run_id}/outcomes/evaluate
GET /analysis-runs/{analysis_run_id}/outcomes
POST /outcome-evaluation-runs/backfill
GET /outcome-evaluation-runs/{run_id}
GET /outcomes/performance/patterns
GET /outcomes/performance/strategy-profiles
GET /outcomes/performance/symbols
```

Evaluation request:

```json
{
  "horizonsMinutes": [5, 15, 30, 60],
  "forceRecompute": false
}
```

Backfill is bounded by `limit` and never performs unbounded database scans.

## Aggregation

Stored outcomes can be aggregated on demand by pattern, strategy profile, or symbol/timeframe. Metrics include:

- evaluated count
- continuation count
- partial follow-through count
- reversal count
- no follow-through count
- insufficient data count
- continuation rate
- reversal rate
- historical follow-through rate
- average favorable, adverse, and net movement
- average pip/tick movement where symbol metadata supports it

The aggregation layer intentionally avoids broker-accounting, account-return, and certainty language.

## Verification

Tests were added for the calculator and service seams, but no builds, tests, Ruff, mypy, pytest, Alembic, app startup, or verification commands were run for this implementation because the user requested file edits only.
