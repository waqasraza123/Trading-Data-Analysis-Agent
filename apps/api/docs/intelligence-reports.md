# Read-Only Intelligence Reports

The intelligence report module composes existing persisted backend artifacts into bounded
operator/UI payloads. It does not persist reports, mutate signals, run replay, execute action
items, evaluate outcomes, run diagnostics, or generate LLM output.

Deterministic artifacts remain the source of truth. LLM explanation and scenario reasoning
sections are included only when previously persisted and safe to expose.

## Endpoints

```txt
GET /intelligence-reports/signals/{signal_id}
GET /intelligence-reports/analysis-runs/{analysis_run_id}
GET /intelligence-reports/reasoning-runs/{reasoning_run_id}
GET /intelligence-reports/outcomes/{outcome_id}
GET /intelligence-reports/signals/{signal_id}/outcomes
GET /intelligence-reports/screenshot-decisions/{decision_id}
```

Query parameters:

```txt
includeAudit=true
includeReasoning=true
includeActions=true
includeOutcomes=true
includeDiagnostics=true
limitAudit=100
limitEvidence=50
```

## Top-Level Contract

Every report uses the same top-level shape:

```json
{
  "reportType": "signal_report",
  "generatedAt": "2026-04-30T00:00:00Z",
  "workspaceId": "uuid",
  "subject": {
    "type": "signal",
    "id": "uuid"
  },
  "sections": {},
  "warnings": [],
  "missingSections": []
}
```

`missingSections` is expected when optional persisted artifacts do not exist yet, such as
diagnostics, news correlations, reasoning runs, outcomes, human review data, or LLM explanations.

## Report Types

`signal_report` includes signal summary, evidence, confidence components, risk notes,
deterministic explanation, news correlations, latest safe LLM explanation, latest scenario
reasoning, action plan, outcomes, historical behavior, audit timeline, and human review links.

`analysis_run_report` includes run metadata, source/candle context, feature and indicator snapshot
summaries, pattern candidates, linked signal summary, deterministic explanation, news correlations,
outcomes, replay metadata, action plan, and audit timeline.

`reasoning_run_report` includes provider/model metadata, prompt version, safety and grounding
status, redacted input snapshot summary, persisted scenario hypotheses, suggested backend actions,
linked signal summary, action plan, blocked/grounding issues, and audit events.

`outcome_report` includes signal summary, outcomes by horizon, reference price/time, future
window, movement measurements, aggregation context, historical behavior summary, limitations, and
audit events.

`screenshot_decision_report` includes screenshot run metadata, extracted OHLC context summary,
linked analysis/signal metadata, human review metadata, correction lineage, and audit events.
It never includes raw screenshot bytes or a full raw candle series.

## Truncation

Reports are bounded:

```txt
evidence rows: 50 by default
audit events: 100 by default
scenario hypotheses: 10
action items: 50
news correlations: 20
pattern candidates: 25
diagnostics: 20
recommendations: 20
```

Bounded sections include `returnedCount`, `totalCount`, and `truncated`.

## Redaction

Reports recursively redact secret-like and raw-payload fields, including API keys, tokens,
passwords, database URLs, raw provider payloads, screenshot/image payloads, and full raw candle
series.

Unsafe blocked LLM output is not exposed. The report keeps safety and grounding metadata so an
operator can see that an output existed and why it was blocked.

## Safety

Reports are read-only market intelligence packets. They do not provide financial advice, broker
execution, order placement, copy trading, auto-trading, alerts, or notifications.

Reports do not recommend buy/sell/enter/exit/leverage actions, do not imply guaranteed behavior,
and do not classify or override deterministic signals with LLM output.
