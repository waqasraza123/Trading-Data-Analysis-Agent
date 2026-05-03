# Actionable Setup Context

Setup context is a backend-only market-intelligence layer that turns existing persisted artifacts
into structured, non-advisory context for daily analysis. It does not classify signals, mutate
signals, change strategy profiles, execute action items, place orders, send alerts, call brokers,
call LLMs for classification, or provide financial advice.

It reads existing signal, evidence, confidence, risk, feature, advanced feature, market regime,
market session, multi-timeframe, cross-asset, outcome, data-quality, and readiness artifacts when
available. Optional artifacts are not required.

## Language Boundary

Allowed language:

- directional bias
- setup context
- invalidation context
- observation zone
- target context
- wait condition
- avoid reason
- review required
- data stale
- evidence conflict
- monitor final candle close
- not a trade instruction

Blocked language includes direct market actions, order language, leverage language, and direct
profit/risk management wording. Setup context must not tell a user to buy, sell, enter, exit, place
orders, use leverage, or treat any zone as an instruction.

## Stored Artifact

`setup_contexts` stores one row per `signal_id` and `context_version`.

Core fields:

- `directional_bias`: `bullish`, `bearish`, `neutral`, or `unclear`
- `setup_quality_label`: `strong_context`, `acceptable_context`, `mixed_context`,
  `review_required`, `avoid_condition`, or `insufficient_context`
- `setup_quality_score`: deterministic score from existing artifacts
- JSON sections for invalidation context, observation zones, target context zones, wait conditions,
  avoid reasons, timeframe agreement, data-quality warnings, risk notes, next observations, and
  metadata

## Invalidation Context

Invalidation context describes levels or conditions where the current directional context weakens.
It is derived from deterministic artifacts such as nearby support/resistance zones and recent final
candle range high/low. It is not a stop-loss instruction and must not be shown as one.

## Observation Zones

Observation zones are nearby support, resistance, or recent range zones to monitor. They are built
from advanced feature support/resistance JSON when available, with recent final candle range as a
fallback. They are not entries.

## Target Context

Target context zones describe plausible next support/resistance/range context for analysis. They are
not take-profit instructions and must not be presented as realized or guaranteed movement.

## Setup Quality

The builder combines:

- persisted signal confidence
- evidence alignment or conflict
- risk note severity
- market regime agreement
- multi-timeframe agreement
- data quality and stale-data context
- recent outcome context when available
- decision-readiness warnings when available

The output remains deterministic context. It does not override the original signal and does not
update strategy profile behavior.

## APIs

```txt
POST /signals/{signal_id}/setup-context?forceRecompute=false
GET /signals/{signal_id}/setup-context
POST /analysis-runs/{analysis_run_id}/setup-context?forceRecompute=false
GET /analysis-runs/{analysis_run_id}/setup-context
```

POST requests are idempotent for the active `SETUP_CONTEXT_VERSION` unless `forceRecompute=true`.

## Settings

```txt
SETUP_CONTEXT_VERSION=v1
SETUP_CONTEXT_STRONG_THRESHOLD=0.7500
SETUP_CONTEXT_ACCEPTABLE_THRESHOLD=0.6000
SETUP_CONTEXT_REVIEW_THRESHOLD=0.4500
```

Thresholds must be ordered strong >= acceptable >= review.

## Future Dashboard Use

Future UI or reports can show setup context as reviewable backend intelligence:

- bias and quality label
- invalidation context
- observation zones
- target context zones
- wait conditions and avoid reasons
- data-quality warnings
- next backend-safe observations

The dashboard must preserve the same language boundary and must not convert context zones into
instructions.
