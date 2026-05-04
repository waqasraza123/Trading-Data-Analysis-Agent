# Pattern Detector Attribution

Pattern detector attribution is a backend-only diagnostic layer over existing persisted pattern
candidates, final signals, signal risk notes, and stored signal outcomes. It explains candidate
contribution after classification has already happened.

It does not mutate pattern candidates, change pattern detectors, alter final signal classification,
auto-tune strategy profiles, call LLMs, send alerts, execute broker workflows, or provide financial
advice.

## Purpose

The runner answers diagnostic questions:

- Which detector types frequently produce selected candidates.
- Which detector types produce high-strength candidates that are often rejected.
- Which selected candidates later show continuation, partial follow-through, no-follow-through, or reversal observations.
- Whether fakeout and chop candidates are acting as directional blockers.
- Which detector types need operator review based on stored observed outcomes.

## Definitions

`selected candidate` means the candidate id matches `signals.selected_pattern_candidate_id` and the
final signal remains directional or otherwise non-blocking.

`rejected candidate` means another candidate was selected for the same final signal.

`blocked candidate` means a fakeout or chop candidate was selected for a `no_signal` result with
`fakeout_risk` or `chop_or_sideways_market` evidence from signal reason or risk notes.

`observed outcome` means a stored `signal_outcomes` row exists for the final signal and requested
horizon. Outcome labels are attached only to selected or blocked candidates because outcomes are
signal-level artifacts.

## Safe Rates

Results store diagnostic rates only:

- `continuationRate`
- `reversalRate`
- `noFollowThroughRate`

Continuation rate includes both continuation and partial follow-through counts. For blocked
fakeout/chop candidates, stored `sideways_after_signal` and `not_directional` outcomes count as
no-follow-through observations for blocker-effectiveness diagnostics.

The module uses continuation rate, reversal rate, no-follow-through rate, observed behavior, and
candidate attribution terminology. It avoids broker-accounting and directional recommendation
language.

## Labels

Attribution labels:

- `strong_selected_behavior`
- `often_rejected`
- `reversal_prone`
- `blocking_effective`
- `mixed`
- `low_sample`
- `insufficient_data`

Labels are diagnostic only. They are intended for detector review and operator analysis, not
automatic profile or detector changes.

## Settings

```txt
PATTERN_ATTRIBUTION_VERSION=v1
PATTERN_ATTRIBUTION_MINIMUM_SAMPLE_SIZE=20
PATTERN_ATTRIBUTION_HIGH_REJECTION_RATE=0.50
PATTERN_ATTRIBUTION_HIGH_REVERSAL_RATE=0.35
```

## APIs

Run attribution:

```http
POST /pattern-attribution/run
```

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "filters": {
    "patternType": null,
    "strategyProfileKey": null,
    "symbolId": null,
    "timeframe": null,
    "startTime": null,
    "endTime": null,
    "limit": 5000
  },
  "horizonsMinutes": [15, 30, 60],
  "minimumSampleSize": 20
}
```

List runs:

```http
GET /pattern-attribution/runs?workspace_id={workspace_id}&limit=100&offset=0
```

Get one run:

```http
GET /pattern-attribution/runs/{run_id}
```

List run results:

```http
GET /pattern-attribution/runs/{run_id}/results
```

Optional result filters:

```http
GET /pattern-attribution/runs/{run_id}/results?pattern_type=fakeout&attribution_label=blocking_effective
```

## Product Boundary

Pattern detector attribution:

- reads existing `pattern_candidates`, `analysis_runs`, `signals`, `signal_risk_notes`, and `signal_outcomes`;
- stores attribution runs and result rows;
- does not create or evaluate signal outcomes;
- does not mutate candidates, detectors, signals, strategy profiles, explanations, outcomes, or quality gates;
- does not run replay, market scans, provider polling, LLM classification, alerts, broker actions, or auto-trading.
