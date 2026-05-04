# Deterministic Signal Review Priority

Signal priority scoring persists a deterministic review priority score for stored signals. It helps
operators decide which signals to review first. It is not trade advice, not directional confidence,
not broker execution, not auto-trading, and not a signal classifier.

The module lives under `app.modules.signal_priority` and writes only to
`signal_priority_scores`. Existing `signals`, classifier outputs, strategy profiles, outcomes, and
context artifacts remain unchanged.

## Score Components

Each component returns a score from `0` to `1`, a reason, a source artifact, and a missing flag:

- `confidence_component`: stored signal confidence score.
- `setup_quality_component`: latest setup context quality score when available.
- `freshness_component`: latest market memory freshness label when available.
- `data_quality_component`: latest data quality run score when available.
- `timeframe_agreement_component`: multi-timeframe agreement score or setup context agreement.
- `cross_asset_component`: cross-asset alignment and data-quality context.
- `historical_reliability_component`: historical case similarity and outcome summary context.
- `readiness_component`: latest decision readiness label and score.
- `quality_gate_component`: intelligence quality run, findings, and shadow classification agreement.
- `outcome_reliability_component`: stored outcomes, confidence calibration, and cohort drift context.

Optional context degrades gracefully. Missing artifacts add `missing_context` warnings and do not
fail scoring.

## Penalties And Boosters

Penalties are deterministic and persisted in `penalties_json`:

- stale data
- low data quality
- conflicting evidence
- no directional signal, neutral, or unclear signal context
- unresolved critical review blockers
- failed grounding or safety quality findings
- pending data recovery
- high or critical risk notes

Boosters are deterministic and persisted in `boosters_json`:

- high confidence
- strong setup context
- fresh data
- aligned multi-timeframe context
- acceptable data quality
- historically stable profile or pattern context when available
- recent observed follow-through when available
- pending human review urgency

The final score is bounded to `0..1` and stored in `priority_score`.

## Priority Labels

`priority_label` can be:

- `urgent_review`
- `high`
- `medium`
- `low`
- `avoid`
- `stale`

Labels are review-priority labels only. They do not express order intent, expected account result,
or directional recommendation.

## Review Buckets

`review_bucket` can be:

- `high_quality_context`
- `needs_confirmation`
- `conflicted`
- `avoid_or_no_directional_signal`
- `stale_or_data_issue`
- `review_required`

Buckets are intended for dashboard and triage grouping. They use safe review language such as
`review first`, `needs confirmation`, `conflicted`, `avoid condition`, `stale data`, and
`review recommended`.

## Settings

Environment-backed settings:

- `SIGNAL_PRIORITY_VERSION`, default `v1`
- `SIGNAL_PRIORITY_HIGH_THRESHOLD`, default `0.75`
- `SIGNAL_PRIORITY_MEDIUM_THRESHOLD`, default `0.55`
- `SIGNAL_PRIORITY_STALE_PENALTY`, default `0.30`
- `SIGNAL_PRIORITY_CONFLICT_PENALTY`, default `0.25`
- `SIGNAL_PRIORITY_REVIEW_REQUIRED_THRESHOLD`, default `0.50`

## APIs

```txt
POST /signals/{signal_id}/priority-score?forceRecompute=false
GET /signals/{signal_id}/priority-score
GET /signal-priorities?workspaceId={workspace_id}&limit=100&offset=0
POST /signal-priorities/workspaces/{workspace_id}/score-recent?limit=500&forceRecompute=false
```

List filters:

- `priorityLabel`
- `reviewBucket`
- `symbolId`
- `timeframe`

## Web Workflow Use

The command center and triage board read `GET /signals/{signal_id}/priority-score` and sort review
cards by `priority_score` when available. If the endpoint or score row is unavailable, the board
keeps its existing deterministic triage classification and time-based fallback ordering.

This module should remain backend-first, deterministic, and non-advisory. Future work can add
workspace-level batch scoring jobs, richer dashboard filters, and operator review analytics without
mutating existing signals or changing classifier behavior.
