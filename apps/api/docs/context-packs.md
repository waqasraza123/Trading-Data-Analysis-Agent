# Unified Analysis Context Packs

Context packs are bounded, redacted, typed intelligence artifact bundles for downstream backend
modules. They compose existing persisted artifacts around a subject without mutating state or
triggering new work.

They are source-of-truth artifact snapshots for reasoning, LLM explanations, scenario ensembles,
decision readiness, intelligence reports, audit timelines, quality gates, historical case retrieval,
dataset exports, operator reviews, and playbooks.

Context packs are backend-only. They do not call LLM providers, call market data providers, run
replay, evaluate outcomes, execute action items, send alerts, create notifications, classify
signals, or provide financial advice.

## Endpoints

```txt
GET /context-packs/signals/{signal_id}
GET /context-packs/analysis-runs/{analysis_run_id}
GET /context-packs/reasoning-runs/{reasoning_run_id}
GET /context-packs/outcomes/{outcome_id}
GET /context-packs/chart-screenshot-runs/{run_id}
```

Query parameters:

```txt
includeAudit=true
includeReasoning=true
includeActions=true
includeOutcomes=true
includeDiagnostics=true
includeQuality=true
includeReports=true
includeScreenshots=true
maxEvidenceRows=50
maxAuditEvents=100
maxOutcomes=20
```

## Top-Level Contract

```json
{
  "contextPackVersion": "v1",
  "subject": {
    "type": "signal",
    "id": "uuid"
  },
  "workspaceId": "uuid",
  "generatedAt": "2026-05-02T00:00:00Z",
  "sections": {},
  "missingSections": [],
  "warnings": [],
  "truncation": {},
  "redaction": {}
}
```

`missingSections` lists optional persisted artifacts that were not available. Missing sections are
normal for modules that have not run yet, such as reasoning, outcomes, quality gates, diagnostics,
market regime snapshots, market session snapshots, advanced features, historical cases, event
studies, and decision readiness.

## Section Structure

Signal context packs include signal summary, analysis run metadata, symbol/timeframe context,
strategy profile snapshot, selected pattern candidate, evidence, confidence components, risk notes,
deterministic explanation, safe LLM explanation metadata/output, news correlations, outcomes,
advanced features, market regime, market session, multi-timeframe context, historical cases,
reasoning runs, action plans, quality runs, decision readiness, audit timeline, screenshot artifacts,
and reproducibility manifest.

Analysis run context packs include run metadata, candle policy, source metadata, feature and
indicator snapshot summaries, advanced feature snapshots, pattern candidates, linked signal summary,
deterministic explanation, news correlations, outcomes, replay links, action plans, audit events, and
event studies.

Reasoning run context packs include run metadata, input snapshot summary, scenario hypotheses,
safety and grounding status, action plan state, linked signal summary, and blocked or grounding
issues. Raw provider credentials and raw provider payloads are never included.

Outcome context packs include outcome metadata, parent signal, horizon, movement measurements,
label/status, parent analysis run, and related profile, pattern, session, and regime artifacts when
persisted.

Chart screenshot run context packs include screenshot run metadata, parser and extraction metadata,
OCR status, review/correction state, linked analysis and signal metadata, bounded extracted payload
summary, and warnings. Raw image bytes and raw full OCR payloads are not included.

## Redaction And Truncation

Context packs recursively redact keys containing:

```txt
api_key
apikey
authorization
credential
database_url
password
private_key
secret
token
```

They also redact raw image, base64, screenshot, provider payload, OCR payload, and raw candle-series
fields. `DATABASE_URL` and provider credentials are never exposed.

Large strings are truncated to `CONTEXT_PACK_MAX_TEXT_LENGTH`. Bounded list sections expose
`returnedCount`, `totalCount`, and `truncated`. The top-level `truncation` object records affected
paths, and `redaction` records redacted paths and unsafe market-action language replacements.

Default limits:

```txt
CONTEXT_PACK_MAX_EVIDENCE_ROWS=50
CONTEXT_PACK_MAX_RISK_NOTES=50
CONTEXT_PACK_MAX_AUDIT_EVENTS=100
CONTEXT_PACK_MAX_OUTCOMES=20
CONTEXT_PACK_MAX_SCENARIOS=10
CONTEXT_PACK_MAX_ACTION_ITEMS=50
CONTEXT_PACK_MAX_NEWS_CORRELATIONS=20
CONTEXT_PACK_MAX_TEXT_LENGTH=4000
CONTEXT_PACK_SCHEMA_VERSION=v1
```

## Read-Only Behavior

The builder only reads persisted artifacts. It does not persist context packs, create database
tables, mutate existing signals, trigger LLM calls, run replay, evaluate outcomes, execute action
items, call external providers, or send alerts or notifications.

The pack is deterministic for the same persisted artifacts and options, except for `generatedAt`.

## Future Use

Downstream modules should use context packs when they need a bounded source-of-truth artifact bundle
instead of independently querying signals, analysis runs, explanations, outcomes, audit events,
quality gates, reports, and screenshot artifacts.

Context packs should remain a safe composition layer, not a classifier, advisory engine, execution
engine, alert system, or financial advice path.
