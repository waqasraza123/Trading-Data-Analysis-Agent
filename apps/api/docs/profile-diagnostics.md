# Outcome-Based Profile Diagnostics

Profile diagnostics turn stored signal outcomes into deterministic backend intelligence for operator
review. They read persisted signals and outcomes, compute observed behavior by strategy profile,
pattern, symbol, timeframe, and horizon, then store advisory calibration recommendations.

This is not financial advice, broker execution, auto-trading, copy trading, or automatic
optimization. Diagnostics do not mutate strategy profiles, classifier thresholds, action plans, or
signals.

## Meaning

Diagnostics describe historical follow-through behavior in stored final-candle outcomes:

- continuation rate
- reversal rate
- no-follow-through rate
- evidence quality through sample size and insufficient-data counts
- average confidence score
- average favorable, adverse, and net movement
- average pip/tick movement where symbol metadata supports it
- confidence alignment score

The language is intentionally limited to market-intelligence terms. It avoids profit, guaranteed
performance, trade instructions, and broker execution concepts.

## Runs

Diagnostic runs are stored in `strategy_profile_diagnostic_runs`. Each run requires a workspace,
explicit horizons, and a bounded `limit`. Optional filters can scope the run by strategy profile,
symbol, timeframe, pattern, and reference-time range.

Run statuses:

- `pending`
- `running`
- `completed`
- `completed_with_warnings`
- `failed`

Scope types:

- `workspace`
- `strategy_profile`
- `symbol`
- `timeframe`
- `pattern`
- `custom`

## Profile Diagnostics

Profile diagnostics are stored in `strategy_profile_diagnostics`.

Rows are generated for profile-level behavior and profile/symbol/timeframe behavior. This supports
both broad profile review and more cautious review for specific symbol/timeframe combinations.

Diagnostic labels:

- `strong_follow_through`
- `mixed_behavior`
- `reversal_prone`
- `low_sample`
- `insufficient_data`
- `needs_threshold_review`
- `neutral`

Rates use evaluated directional outcomes only. Insufficient-data and non-directional outcomes are
counted for coverage but excluded from continuation, reversal, no-follow-through, and confidence
alignment denominators.

## Pattern Diagnostics

Pattern diagnostics are stored in `pattern_outcome_diagnostics`.

Rows are generated for pattern-level behavior and pattern/profile/symbol/timeframe behavior. They
help identify patterns that frequently show reversal or no-follow-through behavior in stored
outcomes.

## Confidence Alignment

Confidence alignment is a deterministic v1 calibration score from `0` to `1`.

Directional continuation and partial follow-through are treated as aligned with higher confidence.
Reversal and no-follow-through are treated as weaker alignment for high confidence. Neutral,
no-signal, unclear, and not-directional outcomes are excluded from directional alignment.

The score is not accuracy and is not a performance guarantee. If the evaluated sample is below the
minimum sample size, the score is null.

## Recommendations

Recommendations are stored in `calibration_recommendations` and are advisory records only.

Recommendation types:

- `review_minimum_confidence`
- `review_candidate_strength`
- `tighten_profile_filter`
- `loosen_profile_filter`
- `review_pattern_detector`
- `increase_sample_size`
- `monitor_symbol_timeframe`
- `no_change`

Statuses:

- `open`
- `acknowledged`
- `dismissed`
- `applied_manually`

Recommendations never auto-apply. Suggested changes are written as review payloads for an operator
or future UI, not as mutations to `strategy_profiles`.

## Configuration

Defaults:

```txt
PROFILE_DIAGNOSTICS_MINIMUM_SAMPLE_SIZE=20
PROFILE_DIAGNOSTICS_STRONG_FOLLOW_THROUGH_RATE=0.65
PROFILE_DIAGNOSTICS_HIGH_REVERSAL_RATE=0.35
PROFILE_DIAGNOSTICS_HIGH_NO_FOLLOW_THROUGH_RATE=0.40
PROFILE_DIAGNOSTICS_CONFIDENCE_MISALIGNMENT_THRESHOLD=0.45
```

## APIs

```txt
POST /profile-diagnostics/run
GET /profile-diagnostics/runs/{run_id}
GET /profile-diagnostics/strategy-profiles
GET /profile-diagnostics/patterns
GET /profile-diagnostics/recommendations
PATCH /profile-diagnostics/recommendations/{recommendation_id}
```

Run request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "strategyProfileKey": null,
  "symbolId": null,
  "timeframe": null,
  "patternType": null,
  "horizonsMinutes": [15, 30, 60],
  "minimumSampleSize": 20,
  "startTime": null,
  "endTime": null,
  "limit": 5000
}
```

Recommendation status update:

```json
{
  "status": "acknowledged"
}
```

## Audit

When diagnostics are based on outcomes linked to analysis runs, the service writes analysis audit
events for diagnostic start, completion, failure, and recommendation creation. Recommendation status
updates are persisted on the recommendation record.

## Not Included

This phase does not add UI, automatic profile mutation, broker execution, auto-trading,
alerts/notifications, billing, ML training, or scheduled diagnostics workers.
