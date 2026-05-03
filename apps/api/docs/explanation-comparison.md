# Explanation Comparison

Explanation comparison is a deterministic review-intelligence layer over persisted explanation
artifacts. It compares deterministic explanations, grounded LLM explanations, scenario reasoning,
and scenario ensemble context for consistency.

It does not call LLM providers, generate explanations, mutate existing explanations, classify
signals, execute broker actions, send alerts, or provide financial advice.

## Purpose

The module answers:

- whether the latest persisted LLM explanation matches the deterministic explanation and signal
- whether persisted LLM or reasoning text mentions unsupported evidence, news, numbers, or patterns
- whether important persisted risk notes are omitted from the LLM explanation
- whether scenario reasoning conflicts with the final signal context
- whether explanation layers are aligned, mixed, or conflicting
- whether operator review is recommended

## Persistence

`explanation_comparison_runs` stores one deterministic comparison result:

```txt
workspace_id
signal_id
analysis_run_id
status
comparison_version
deterministic_explanation_id
llm_explanation_id
reasoning_run_id
alignment_score
alignment_label
summary
metadata_json
created_at
updated_at
```

`explanation_comparison_findings` stores issue-level review findings:

```txt
workspace_id
comparison_run_id
finding_type
severity
code
message
source_reference
metadata_json
created_at
```

Finding types:

```txt
missing_context
contradiction
unsupported_claim
omitted_risk
unsafe_language
causation_language
explanation_mismatch
```

## Comparison Inputs

The service loads persisted records only:

```txt
signal
signal evidence
signal risk notes
deterministic explanation
latest LLM explanation
latest scenario reasoning run and scenarios
signal news correlations
latest scenario ensemble consensus when available
```

Missing optional layers produce findings instead of triggering generation.

## Alignment Scoring

The alignment score starts at `1.0000` and subtracts deterministic severity penalties. The score is
clamped to `0..1`.

Alignment labels:

```txt
aligned
mostly_aligned
mixed
conflicting
insufficient_context
```

Default settings:

```txt
EXPLANATION_COMPARISON_VERSION=v1
EXPLANATION_COMPARISON_ALIGNMENT_THRESHOLD=0.7500
EXPLANATION_COMPARISON_REVIEW_THRESHOLD=0.5000
```

Operator review is recommended in run metadata when the score falls below the review threshold,
when the run is conflicting or insufficient-context, or when high/critical findings exist.

## Safety Checks

The comparator flags:

- persisted safety or grounding status failures
- unsupported news/event mentions when no news correlation exists
- news causation language
- unsupported numeric claims not present in compared persisted artifacts
- unsafe trading instruction or guarantee language
- LLM bias or pattern mismatch against the persisted signal
- omitted medium/high/critical risk notes
- unsupported scenario backend actions
- high-possibility reversal/fakeout scenario mismatch against a directional signal
- scenario ensemble disagreement or insufficient context

## APIs

```txt
POST /signals/{signal_id}/explanation-comparison
GET /signals/{signal_id}/explanation-comparison/latest
GET /explanation-comparisons/{run_id}
GET /explanation-comparisons/{run_id}/findings
```

Run request:

```json
{
  "forceRecompute": false
}
```

If `forceRecompute=false`, the POST endpoint returns the latest run for the same signal and
comparison version when one exists. `forceRecompute=true` creates a new comparison run.

## Not Included

This phase does not add UI, alerts, notifications, automatic operator-review item creation, broker
execution, auto-trading, new explanation generation, LLM provider calls, signal classification, or
financial-advice output.
