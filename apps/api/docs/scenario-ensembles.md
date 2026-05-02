# Scenario Ensemble Consensus

Scenario ensembles run multiple provider/model scenario reasoning requests over the same grounded
signal input and store agreement diagnostics. They compare scenario-level agreement only.

This layer is not prediction, classification, trading advice, alerting, broker execution,
auto-trading, or a final signal generator. It cannot override deterministic signals.

## Purpose

The ensemble layer helps operators inspect whether multiple configured LLM adapters or prompt/model
variants agree on persisted scenario reasoning context:

- continuation
- reversal
- consolidation
- event-driven volatility
- insufficient context

Disagreement is stored as diagnostic context, not as a failure when valid provider outputs exist.

## Provider And Model Comparison

Requests provide up to `SCENARIO_ENSEMBLE_MAX_PROVIDERS` provider/model entries. The default uses
the mock provider so tests and local startup do not require real provider keys.

```json
{
  "providers": [
    {"provider": "mock", "model": "mock-scenario-v1"},
    {"provider": "mock", "model": "mock-scenario-v2"}
  ],
  "forceRecompute": false
}
```

Each provider/model request reuses the existing scenario reasoning service, adapter registry,
parser, safety checks, grounding checks, and persisted `llm_reasoning_runs` /
`scenario_hypotheses` records.

## Consensus Labels

Run-level and scenario-level consensus labels are:

```txt
strong_agreement
partial_agreement
disagreement
insufficient_context
failed
```

The consensus score is the top grounded scenario agreement ratio across valid provider outputs,
degraded when provider outputs are excluded for safety, grounding, fallback, or provider errors.

## Safety And Grounding

Provider output must pass existing reasoning safety and grounding checks before it contributes to
consensus. Unsafe, blocked, failed, fallback, provider-not-configured, and ungrounded outputs are
stored as ensemble items but excluded from consensus.

Unsafe or blocked model text is not exposed through the ensemble consensus result. Operators should
review stored item status, safety status, grounding status, and error messages instead.

## APIs

```txt
POST /signals/{signal_id}/scenario-ensemble
GET /signals/{signal_id}/scenario-ensembles
GET /scenario-ensembles/{ensemble_run_id}
GET /scenario-ensembles/{ensemble_run_id}/items
GET /scenario-ensembles/{ensemble_run_id}/consensus
```

## Settings

```txt
SCENARIO_ENSEMBLE_VERSION=v1
SCENARIO_ENSEMBLE_DEFAULT_PROVIDER=mock
SCENARIO_ENSEMBLE_MAX_PROVIDERS=3
SCENARIO_ENSEMBLE_MIN_AGREEMENT_RATIO=0.6000
```

## Persistence

Ensemble persistence is separate from reasoning persistence:

- `scenario_ensemble_runs` stores request, status, score, label, and aggregate safety/grounding
  diagnostics.
- `scenario_ensemble_items` stores each provider/model attempt and linked reasoning run.
- `scenario_consensus_results` stores scenario-level agreement and conflicting evidence summaries.

Existing reasoning runs are not mutated by ensemble consensus.
