# Walk-Forward Validation

Walk-forward validation analyzes stored deterministic signals and stored signal outcomes across
chronological validation windows. It is a historical diagnostics runner for profile behavior,
pattern behavior, confidence alignment, stability, degradation, and sample coverage.

It is not a profit backtest, broker simulation, alerting workflow, financial-advice feature,
auto-trading feature, or strategy-profile mutation path.

## Purpose

The runner answers backend-only historical questions:

- How profile behavior changed across validation windows.
- Whether a strategy profile stayed stable across weekly or monthly periods.
- Whether confidence alignment degraded over time.
- Which windows had low or insufficient samples.
- Whether a pattern showed different observed follow-through or reversal behavior in later windows.

## Windows

Requests provide `windowDays`, or the service uses `WALK_FORWARD_DEFAULT_WINDOW_DAYS`.
The resolved period is split into consecutive validation windows from `startTime` to `endTime`.

`startTime` and `endTime` may be omitted only when they can be inferred from stored matching
outcome rows. If no matching stored outcomes exist, the run completes with warnings and no
validation windows.

The service reads only bounded existing signals and outcomes. It does not evaluate missing outcomes.

## Safe Metrics

Each validation window is grouped by horizon and stores:

- Sample size and evaluated count.
- Continuation, partial follow-through, no-follow-through, reversal, and insufficient-data counts.
- Observed follow-through rate in `continuationRate`.
- Reversal rate.
- No-follow-through rate.
- Average deterministic confidence score.
- Confidence alignment score when enough evaluated samples exist.
- Stability label: `stable`, `improving`, `degrading`, `mixed`, `low_sample`, or `insufficient_data`.

Comparison rows summarize stability by horizon across sufficient windows and flag degradation or
improvement when changes exceed configured thresholds.

## Product Boundary

Walk-forward validation:

- reads `signals` and `signal_outcomes`;
- stores validation runs, windows, and comparisons;
- does not create outcomes;
- does not mutate existing signals;
- does not modify strategy profiles;
- does not execute trades;
- does not send alerts;
- does not provide financial advice;
- does not calculate broker accounting or profit metrics.

## Settings

```txt
WALK_FORWARD_VALIDATION_VERSION=v1
WALK_FORWARD_DEFAULT_WINDOW_DAYS=30
WALK_FORWARD_MINIMUM_SAMPLE_SIZE=20
WALK_FORWARD_DEGRADATION_THRESHOLD=0.20
WALK_FORWARD_IMPROVEMENT_THRESHOLD=0.20
```

## APIs

Run validation:

```http
POST /walk-forward-validations/run
```

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "name": "Monthly breakout validation",
  "filters": {
    "strategyProfileKey": "breakout_continuation",
    "patternType": null,
    "symbolId": null,
    "timeframe": "1m",
    "startTime": "2026-01-01T00:00:00Z",
    "endTime": "2026-04-01T00:00:00Z",
    "maxSignals": 5000
  },
  "windowDays": 30,
  "horizonsMinutes": [15, 30, 60],
  "minimumSampleSize": 20
}
```

List runs:

```http
GET /walk-forward-validations/runs?workspace_id={workspace_id}&limit=100&offset=0
```

Get one run:

```http
GET /walk-forward-validations/runs/{run_id}
```

List windows:

```http
GET /walk-forward-validations/runs/{run_id}/windows
```

List comparisons:

```http
GET /walk-forward-validations/runs/{run_id}/comparisons
```

## Future Diagnostics Integration

Future diagnostic modules can read walk-forward validation windows and comparisons as historical
stability evidence. They should treat this module as persisted context only and must not use it to
auto-adjust profiles, rewrite confidence scores, mutate signals, send alerts, execute broker
workflows, or produce advice.
