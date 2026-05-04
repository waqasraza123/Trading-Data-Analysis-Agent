# Intelligence Quality Gates

The intelligence quality module adds deterministic validation around completed analysis artifacts
and persisted signals. It answers whether stored artifacts are internally consistent, whether the
final signal agrees with its selected candidate, whether confidence math and evidence direction are
coherent, and whether optional downstream outputs stay grounded in persisted records.

This module is backend-only. It does not classify signals, mutate final signals, mutate strategy
profiles, run replay, evaluate outcomes, execute action items, call LLM providers, send
notifications, or perform broker work.

## Stored Records

`intelligence_quality_runs` stores one quality run for a signal, analysis run, replay, or screenshot
decision source. Runs include a deterministic `quality_score`, a `quality_label`, gate and shadow
versions, summary metadata, and checked time.

`intelligence_quality_findings` stores invariant failures, contradictions, missing artifacts,
degraded-confidence notes, grounding issues, shadow disagreements, safety issues, and review
recommendations.

`shadow_classification_results` stores diagnostic-only profile comparisons. Each row records what
one active strategy profile would have produced against persisted pattern candidates.

## Quality Gates

Quality gates inspect persisted artifacts only:

- required artifact presence for analysis run, signal, feature snapshot, indicator snapshot,
  pattern candidates, confidence components, evidence, and deterministic explanation
- signal/candidate consistency for selected candidate, pattern type, bias, strength, and selected
  flag
- confidence component math, total score, label ranges, component weight normalization, and low
  data-quality context
- evidence direction alignment, non-negative weights, and safe wording
- risk/confidence contradictions and no-signal summary conflicts
- deterministic explanation consistency, cautious news wording, and no causation claims
- optional LLM/reasoning safety and grounding status checks
- outcome compatibility with signal id, bias snapshot, directional labels, metrics, and pip/tick
  conversion metadata
- news correlation label ranges, cautious reason wording, and plausible time deltas
- replay link and engine snapshot consistency
- chart screenshot parser metadata, including unsupported chart flags, review-required state, and
  failed OCR context, without running OCR or treating pixels as source-of-truth analysis

Missing optional artifacts produce low or info findings. Missing required artifacts produce medium
or high findings.

## Scoring

Quality score starts at `1.0` and subtracts deterministic penalties:

- `info`: `0.01`
- `low`: `0.03`
- `medium`: `0.08`
- `high`: `0.18`
- `critical`: `0.35`

The score is clamped to `0..1`.

Labels:

- `strong`: `>= 0.90`
- `acceptable`: `>= 0.75`
- `review_recommended`: `>= 0.50`
- `inconsistent`: `>= 0.20`
- `insufficient_context`: `< 0.20`

Required missing artifacts cap otherwise strong results to review-oriented labels.

The scoring thresholds and persisted versions are configurable:

```txt
INTELLIGENCE_QUALITY_GATE_VERSION=quality_gates_v1
INTELLIGENCE_QUALITY_SHADOW_VERSION=shadow_profiles_v1
INTELLIGENCE_QUALITY_STRONG_THRESHOLD=0.9000
INTELLIGENCE_QUALITY_ACCEPTABLE_THRESHOLD=0.7500
INTELLIGENCE_QUALITY_REVIEW_THRESHOLD=0.5000
```

Thresholds must remain ordered from strong to acceptable to review.

## Shadow Classification

Shadow classification is diagnostic only. It loads active strategy profiles and persisted pattern
candidates, evaluates each profile in memory through the existing deterministic candidate
evaluation helpers, and compares the result to the persisted final signal.

It records:

- `agreed`
- `disagreed_bias`
- `disagreed_pattern`
- `disagreed_status`
- `no_candidate`
- `not_applicable`

Shadow disagreements do not replace the final signal and do not mark candidates selected. They
produce quality findings and review recommendations only.

## Review Recommendations

Review recommendations are stored as findings with `finding_type=review_recommendation`. They are
safe operator review hints, not action items and not automatic requests.

Examples:

- review confidence and severe risk-note contradictions
- review shadow profile disagreement
- review ungrounded news context
- review non-directional outcome label conflicts
- review exposed output with failed grounding
- review linked screenshot extraction when parser metadata says human review is required

Suggested backend actions are limited to safe follow-up records:

```txt
evaluate_outcome_after_horizon
run_replay
run_news_correlation
wait_for_more_final_candles
request_human_review
no_action
```

Rejected trading actions such as order placement, position changes, and risk-management instructions
changes, leverage, and copy trading remain invalid and are never made executable.

## APIs

```txt
POST /intelligence-quality/signals/{signal_id}/run
GET /intelligence-quality/signals/{signal_id}/latest
GET /intelligence-quality/runs/{quality_run_id}
POST /intelligence-quality/analysis-runs/{analysis_run_id}/run
GET /intelligence-quality/analysis-runs/{analysis_run_id}/latest
GET /intelligence-quality/runs/{quality_run_id}/findings
GET /intelligence-quality/runs/{quality_run_id}/shadow-classifications
```

Run request:

```json
{
  "includeShadowClassification": true,
  "forceRecompute": false
}
```

Response:

```json
{
  "qualityRun": {
    "id": "00000000-0000-0000-0000-000000000000",
    "qualityScore": "0.8700",
    "qualityLabel": "acceptable",
    "status": "completed"
  },
  "findings": [],
  "shadowClassifications": []
}
```

If a latest run already exists for the same source, gate version, and shadow version,
`forceRecompute=false` returns it. `forceRecompute=true` creates a new run.

## UI Use

The web `/quality` page composes stored quality, outcome, calibration, validation, drift,
attribution, and cohort artifacts into a read-only scoreboard. It shows observed behavior,
confidence alignment, data coverage, and review warnings only. It does not run diagnostics
automatically, calculate account results, execute broker workflows, send notifications, or provide
financial advice.

## Not Included

This phase does not add auto-correction, automatic profile mutation, broker execution,
auto-trading, alerts, billing, ML training, or external provider credentials.
