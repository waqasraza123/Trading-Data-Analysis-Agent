# Deterministic Signal Classification

This slice adds deterministic strategy profiles and final signal classification. It does not add LLM explanations, news correlation, broker execution, alerts, live scanner expansion, UI, or financial-advice output.

## Boundary

Signal classification runs after pattern candidates are persisted:

```txt
analysis run
-> candle preflight
-> feature snapshot
-> indicator snapshot
-> pattern candidates
-> deterministic strategy profile classification
-> signals, confidence components, evidence, risk notes
-> deterministic explanation
```

Market data remains the source of truth. Pattern candidates are persisted first, rules classify them, and later AI layers may only explain stored evidence.

## Strategy Profiles

New table:

```txt
strategy_profiles
```

Default profiles are seeded idempotently:

```txt
breakout_continuation v1
reversal_rejection v1
range_chop_avoidance v1
fakeout_protection v1
```

Profiles are deterministic analysis configurations. They define allowed/excluded patterns, minimum strength/confidence, component weights, risk filters, and no-signal rules.

The current pattern taxonomy supports:

```txt
bullish_breakout
bearish_breakdown
bullish_continuation
bearish_continuation
bullish_reversal
bearish_reversal
fakeout
sideways_range
low_volatility_chop
```

`support_bounce` and `resistance_rejection` are not seeded because the current detector taxonomy does not emit them.

## Signal Tables

Final outputs are stored in:

```txt
signals
signal_confidence_components
signal_evidence
signal_risk_notes
```

There is one current signal per analysis run. Reclassification replaces the previous signal for that run and snapshots the selected strategy profile config so old outputs remain reproducible.

Confidence components are:

```txt
pattern_strength
trend_alignment
volatility_confirmation
indicator_support
data_quality
```

Missing feature or indicator data uses a degraded neutral score and adds a risk note instead of crashing.

## Conflict Resolution

The resolver is deterministic:

- fakeout protection blocks breakout/continuation when fakeout strength is within the configured margin
- range/chop avoidance blocks directional output when chop or sideways evidence is close enough
- opposing bullish and bearish candidates inside the configured margin produce `unclear`
- reversal beats continuation only when strength and confidence both clear the configured reversal margin
- low data quality can produce `insufficient_evidence`

No-signal reasons are stable codes such as:

```txt
no_pattern_candidates
no_profile_candidates
below_minimum_strength
below_minimum_confidence
conflicting_directional_candidates
fakeout_risk
chop_or_sideways_market
low_data_quality
insufficient_evidence
unsupported_pattern_type
```

## API

```txt
GET /strategy-profiles
GET /strategy-profiles/{key}
POST /analysis-runs/{analysis_run_id}/classify
GET /analysis-runs/{analysis_run_id}/signal
GET /signals/{signal_id}
POST /signals/{signal_id}/deterministic-explanation
GET /signals/{signal_id}/deterministic-explanation
```

Manual classification only accepts completed runs. Automatic classification runs inside the analysis lifecycle before the run is marked completed. Deterministic explanations are generated after classification and summarize only stored artifacts.

## Tests

Unit and golden tests cover:

```txt
profile defaults
candidate filtering
minimum strength and confidence rejection
weighted confidence scoring
missing snapshot degradation
fakeout protection
range/chop no-signal
directional conflicts
reversal-vs-continuation margins
selected profile snapshots
deterministic explanation summaries and safety fallback
golden bullish/bearish/fakeout/chop/reversal/conflict scenarios
```
