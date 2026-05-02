# Decision Readiness Assessment

Decision readiness assesses whether persisted backend intelligence has enough supporting context
for operator review. It is not trade readiness, order readiness, financial advice, or an execution
signal.

## Purpose

The readiness engine reads existing artifacts and stores assessment rows with deterministic scores,
labels, blockers, warnings, and missing context. It must never mutate source artifacts.

Expected routes:

```txt
POST /decision-readiness/signals/{signal_id}/assess
GET /decision-readiness/signals/{signal_id}/latest
POST /decision-readiness/analysis-runs/{analysis_run_id}/assess
GET /decision-readiness/analysis-runs/{analysis_run_id}/latest
GET /decision-readiness
```

## Settings

```txt
DECISION_READINESS_ASSESSMENT_VERSION=decision_readiness_v1
DECISION_READINESS_READY_THRESHOLD=0.8500
DECISION_READINESS_REVIEW_THRESHOLD=0.6500
```

## Integration Inputs

Readiness may read:

- signal artifacts
- deterministic explanations
- quality findings
- unresolved operator reviews
- backend-safe action items
- observed outcomes
- market regime context
- historical case vector/search availability
- profile diagnostics
- chart screenshot metadata

Missing optional modules should produce missing-context entries, warnings, or neutral sections, not
runtime generation.

## Safety

Decision readiness is diagnostic only. It must not execute action items, run replay, evaluate
outcomes, call LLMs, generate vectors, generate regime context, auto-create review items, mutate
signals, update strategy profiles, send notifications, call brokers, or provide financial advice.
