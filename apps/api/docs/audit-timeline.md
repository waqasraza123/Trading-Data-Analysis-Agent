# Audit Timeline Traceability API

The audit timeline module exposes read-only traceability views for persisted market intelligence
artifacts. It answers what happened before and after a decision artifact was created without
running analysis, replay, outcome evaluation, scenario reasoning, LLM generation, action execution,
notifications, broker workflows, or financial-advice logic.

## Supported Subjects

```txt
GET /audit-timeline/analysis-runs/{analysis_run_id}
GET /audit-timeline/signals/{signal_id}
GET /audit-timeline/reasoning-runs/{reasoning_run_id}
GET /audit-timeline/action-plans/{action_plan_id}
GET /audit-timeline/outcomes/{outcome_id}
GET /audit-timeline/chart-screenshot-runs/{run_id}
```

Each response includes `subject`, `workspaceId`, `generatedAt`, `completeness`, `timeline`,
`artifactGraph`, `sections`, and `warnings`.

## Timeline Events

Timeline events are chronological and bounded. Events come from existing audit logs when available
and from synthetic timestamps on persisted artifacts when audit logs are missing. Synthetic events
can represent analysis run creation, candle window resolution, feature and indicator snapshots,
pattern candidates, signal evidence/confidence/risk persistence, deterministic explanations, news
correlations, LLM explanations, outcomes, reasoning runs, action plans, replay links, screenshot
decisions, human reviews, correction lineage, scheduled scan provenance, quality findings, and
shadow classification diagnostics.

The API never includes raw candle series or raw image bytes.

## Artifact Graph

The artifact graph links stored backend artifacts with relationships: `produced`, `derived_from`,
`explained_by`, `reviewed_by`, `replayed_from`, `evaluated_by`, `correlated_with`, and
`planned_action`.

The graph is an operator/UI contract for inspecting lineage. It does not mutate source artifacts
and is not persisted as a snapshot.

## Completeness Score

Completeness is deterministic traceability coverage only. It is not a signal-quality, broker-accounting,
or recommendation metric.

Labels:

```txt
complete: score >= 0.80
partial:  score >= 0.45 and < 0.80
sparse:   score < 0.45
```

Missing optional artifacts are reported under `completeness.missingSections`. They do not cause the
timeline route to fail.

## Query Bounds

```txt
includeAudit=true
includeGraph=true
includeArtifacts=true
includeMetadata=true
limitEvents=200
limitAudit=100
limitArtifacts=200
```

Defaults come from `AUDIT_TIMELINE_MAX_EVENTS`, `AUDIT_TIMELINE_MAX_AUDIT_EVENTS`,
`AUDIT_TIMELINE_MAX_ARTIFACTS`, and `AUDIT_TIMELINE_REDACTION_ENABLED`. `limitEvents`,
`limitAudit`, and `limitArtifacts` are capped at 500. Metadata is truncated and large collections
are summarized.

## Redaction And Truncation

Metadata redacts keys containing `api_key`, `token`, `secret`, `password`, `database_url`,
`authorization`, `credential`, or `private_key`.

The sanitizer also redacts raw/base64 image payloads, raw provider payloads, raw candle lists, and
stack traces. Public timeline summaries redact unsafe trading-advice phrases such as direct buy/sell
or order-placement instructions.

## Read-Only Behavior

Audit timelines compose existing persisted artifacts only. They do not run analysis, run replay,
evaluate outcomes, run diagnostics, generate LLM output, execute action items, mutate source
artifacts, send alerts or notifications, or provide broker execution, auto-trading, copy trading,
billing, or financial advice.

Scheduled scan, chart screenshot, and intelligence quality records are included only when already
persisted. Missing optional modules or artifacts become `missingSections` entries or empty sections
rather than runtime work.

## Future Operator Usage

The response shape is designed for a future UI to render a chronological timeline, inspect missing
sections, and visualize artifact lineage. Persisted timeline snapshots and PDF/CSV export are not
implemented in this phase.
