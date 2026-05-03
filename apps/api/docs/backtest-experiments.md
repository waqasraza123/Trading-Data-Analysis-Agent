# Backtest Experiments

Backtest experiments summarize historical behavior across existing persisted signals and signal outcomes. They are cohort analysis jobs, not broker simulations, trade execution systems, or financial-advice workflows.

The runner answers questions such as:

- How a profile or pattern behaved over a bounded historical period.
- How outcomes differed by symbol, timeframe, bias, classification status, confidence label, pattern, strategy profile, and available news correlation context.
- Which cohorts showed more continuation or reversal observations.
- Which cohorts have low or insufficient sample size.
- What observed follow-through characteristics were present in already evaluated outcomes.

## Product Boundary

Backtest experiments only read existing `signals`, `signal_outcomes`, and optional contextual rows such as `signal_news_correlations`. They do not create signal outcomes, evaluate future candles, mutate signals, change strategy profiles, run profile diagnostics, send alerts, place broker orders, or execute trades.

The output avoids profit, PnL, and win-rate terminology. Metrics are historical behavior observations over persisted outcome labels and movement fields.

## Cohorts

Supported cohort dimensions:

- `strategy_profile_key`
- `pattern_type`
- `symbol_id`
- `timeframe`
- `bias`
- `classification_status`
- `confidence_label`
- `news_correlation_label`

Optional dimensions such as `session_label` and `regime_label` are requestable for future compatibility but are skipped safely when no persisted source module exists.

Each cohort is grouped by the requested dimensions and one horizon. Cohorts persist:

- Sample and evaluated counts.
- Continuation, partial follow-through, no follow-through, reversal, and insufficient-data counts.
- Continuation, reversal, and no-follow-through rates.
- Average confidence score.
- Average favorable, adverse, and net movement fields when present.
- A cohort label: `strong_follow_through`, `mixed_behavior`, `reversal_prone`, `low_sample`, `insufficient_data`, or `neutral`.

## API

Run an experiment:

```http
POST /backtest-experiments/run
```

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "name": "Breakout continuation behavior",
  "description": null,
  "filters": {
    "strategyProfileKey": "breakout_continuation",
    "symbolId": null,
    "timeframe": "1m",
    "startTime": null,
    "endTime": null,
    "limit": 5000
  },
  "cohortDimensions": ["pattern_type", "symbol_id", "timeframe"],
  "horizonsMinutes": [15, 30, 60],
  "minimumSampleSize": 20
}
```

List runs:

```http
GET /backtest-experiments/runs?workspace_id={workspace_id}&limit=100
```

Get one run:

```http
GET /backtest-experiments/runs/{run_id}
```

List run cohorts:

```http
GET /backtest-experiments/runs/{run_id}/cohorts
```

## Bounded Reads

`workspaceId` is required and `filters.limit` bounds the source read. The runner does not perform unbounded scans. If no existing outcomes match the filters, the run completes with warnings and no cohorts.
## Integrated Engine Boundary

Backtest experiments read stored signals, outcomes, and deterministic context. They do not call
provider polling, run analysis, evaluate missing outcomes, mutate strategy profiles, alter final
signals, calculate broker accounting, send alerts, or provide financial advice. Public metrics should
use observed behavior, historical follow-through, continuation rate, reversal rate, and cohort result
terminology.
