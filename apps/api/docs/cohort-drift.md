# Signal Cohort Drift Detection

Signal cohort drift detection compares recent stored signal/outcome behavior with a baseline
period. It is backend-only historical behavior monitoring for operator review.

It does not predict future behavior, provide financial advice, mutate signals, mutate outcomes,
modify strategy profiles, send alerts, execute broker actions, call LLMs, or evaluate missing
outcomes.

## Purpose

The engine answers questions such as:

- Are recent `breakout_continuation` signals behaving differently from the baseline period?
- Has reversal behavior increased for a pattern, profile, symbol, or timeframe cohort?
- Has confidence alignment changed between the baseline and recent window?
- Is a cohort too small to judge?
- Which cohorts should operators review?

## Baseline And Recent Window

Each run compares two non-overlapping windows:

- `baselineWindow`: the historical reference period.
- `comparisonWindow`: the recent window being compared against the baseline.

If windows are omitted, the service uses:

```txt
COHORT_DRIFT_DEFAULT_BASELINE_DAYS=90
COHORT_DRIFT_DEFAULT_COMPARISON_DAYS=30
```

The comparison window defaults to the latest configured recent period. The baseline window defaults
to the period immediately before the comparison window.

## Safe Rates

Rates use evaluated directional stored outcomes only. Neutral, unclear, not-directional, failed,
and insufficient-data outcomes are excluded from rate denominators but still affect sample and
coverage labels.

Persisted result fields include:

- `continuationRate`: continuation plus partial follow-through observations divided by evaluated
  directional outcomes.
- `reversalRate`: reversal observations divided by evaluated directional outcomes.
- `noFollowThroughRate`: no-follow-through observations divided by evaluated directional outcomes.
- `confidenceAlignment`: `1 - abs(averageConfidenceScore - continuationRate)` when the evaluated
  sample meets the minimum sample size.

These are historical observed-behavior metrics. They are not broker accounting or guarantee
metrics.

## Cohorts

Supported cohort dimensions:

- `strategy_profile_key`
- `pattern_type`
- `symbol_id`
- `timeframe`
- `bias`
- `confidence_label`
- `market_session_label`
- `market_regime_label`

Market session and market regime values are used only when already persisted for the signal. Missing
context is grouped as `unknown`.

## Labels

Result labels:

- `no_drift`
- `mild_drift`
- `moderate_drift`
- `severe_drift`
- `low_sample`
- `insufficient_data`

Severity:

- `info`
- `low`
- `medium`
- `high`

Low-sample and insufficient-data cohorts always use `info` severity and do not produce severe drift.

## Settings

```txt
COHORT_DRIFT_VERSION=v1
COHORT_DRIFT_MINIMUM_SAMPLE_SIZE=20
COHORT_DRIFT_MILD_THRESHOLD=0.10
COHORT_DRIFT_MODERATE_THRESHOLD=0.20
COHORT_DRIFT_SEVERE_THRESHOLD=0.35
COHORT_DRIFT_DEFAULT_BASELINE_DAYS=90
COHORT_DRIFT_DEFAULT_COMPARISON_DAYS=30
```

## APIs

Run drift detection:

```http
POST /cohort-drift/run
```

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "filters": {
    "strategyProfileKey": "breakout_continuation",
    "symbolId": null,
    "timeframe": "1m",
    "patternType": null,
    "bias": null,
    "confidenceLabel": null,
    "maxOutcomes": 10000
  },
  "baselineWindow": {
    "startTime": "2026-01-01T00:00:00Z",
    "endTime": "2026-04-01T00:00:00Z"
  },
  "comparisonWindow": {
    "startTime": "2026-04-01T00:00:00Z",
    "endTime": "2026-05-01T00:00:00Z"
  },
  "cohortDimensions": ["strategy_profile_key", "pattern_type", "symbol_id"],
  "horizonsMinutes": [15, 30, 60],
  "minimumSampleSize": 20
}
```

List runs:

```http
GET /cohort-drift/runs?workspace_id={workspace_id}&limit=100&offset=0
```

Get one run:

```http
GET /cohort-drift/runs/{run_id}
```

List run results:

```http
GET /cohort-drift/runs/{run_id}/results
```

List recent results:

```http
GET /cohort-drift/results/recent?workspace_id={workspace_id}
```

Result listing supports optional `drift_label`, `severity`, `horizon_minutes`, and `cohort_key`
filters.

## Future Operator Review Integration

Future operator review integration can read `cohort_drift_results` and create review items for
moderate or severe drift. That integration should treat drift results as advisory evidence only and
must not mutate source artifacts, apply profile changes automatically, send alerts, execute actions,
or provide financial advice.
