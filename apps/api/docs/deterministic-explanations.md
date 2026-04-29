# Deterministic Explanations

This slice adds safe deterministic explanation persistence. It does not add LLM calls, news correlation, UI, broker execution, alerts, auto-trading, or financial-advice output.

## Boundary

Explanations are generated after deterministic signal classification:

```txt
signal
-> confidence components
-> signal evidence
-> risk notes
-> selected strategy profile snapshot
-> feature snapshot
-> indicator snapshot
-> deterministic explanation
```

Market data remains the source of truth. Rules classify. The explanation layer only summarizes persisted backend artifacts.

## Table

Final deterministic explanation output is stored in:

```txt
deterministic_explanations
```

There is one current deterministic explanation per signal. Regeneration is idempotent and updates the existing row for the same `signal_id`.

Stored sections:

```txt
short_summary
market_behavior
evidence_summary
confidence_summary
risk_summary
no_signal_summary
full_text
source_snapshot_json
safety_status
blocked_terms_json
```

`source_snapshot_json` stores the structured artifacts used for the explanation and does not duplicate raw candle rows.

## Safety

The safety checker blocks phrases that imply trade instructions, guarantees, leverage, or advice. If blocked language is found, the row is stored with `safety_status=blocked`, blocked terms are captured, and the detailed text is replaced with a fixed safe fallback.

Generated text may describe deterministic bullish or bearish classification, but it must not say to buy, sell, enter, exit, or guarantee movement.

## API

```txt
POST /signals/{signal_id}/deterministic-explanation
GET /signals/{signal_id}/deterministic-explanation
POST /analysis-runs/{analysis_run_id}/deterministic-explanation
GET /analysis-runs/{analysis_run_id}/deterministic-explanation
```

Signal retrieval responses also include `deterministicExplanation` when an explanation exists:

```txt
GET /signals/{signal_id}
GET /analysis-runs/{analysis_run_id}/signal
```

## Lifecycle

Automatic generation runs after signal classification in the normal analysis lifecycle,
after replay signal classification, and after manual classification.

Replay signals receive their own deterministic explanation because explanations are unique
by `signal_id`, not by original analysis run.

Audit events:

```txt
deterministic_explanation_started
deterministic_explanation_generated
deterministic_explanation_blocked
deterministic_explanation_failed
```
