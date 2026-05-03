# Multi-LLM Scenario Reasoning

The scenario reasoning layer is an optional backend intelligence layer over stored deterministic
artifacts. It does not classify signals, override deterministic outputs, execute orders, provide
financial advice, or predict certain outcomes.

## Purpose

Scenario reasoning answers backend-safe questions after a persisted signal exists:

- plausible follow-through, reversal, consolidation, volatility, event-volatility, fakeout, or
  insufficient-context scenarios to monitor
- deterministic evidence supporting or weakening each scenario
- stored outcome history for similar profile, pattern, symbol, timeframe, and horizon conditions
- next observations to watch in future final candles
- backend follow-up actions such as outcome evaluation, replay, news correlation, waiting for more
  final candles, or human review

## Adapter Architecture

Adapters live under `app/modules/llm_adapters/` and implement:

```txt
generate_structured(request: LlmAdapterRequest) -> LlmAdapterResponse
```

The request includes provider, model, system prompt, user prompt, bounded input JSON, response schema
name, output-token budget, temperature, timeout, and metadata. The response includes text, optional
JSON, finish reason, token usage, estimated cost, sanitized raw metadata, and latency.

Supported providers:

- `mock`: deterministic local provider used by tests and local development
- `openai` / `openai_compatible`: generic HTTP chat-completions adapter using `OPENAI_API_KEY` and
  optional `OPENAI_BASE_URL`
- `anthropic`: clean integration stub that reports provider-not-configured until production wiring
  is intentionally added

Adding Gemini, Ollama, OpenRouter, or another provider should only require a new adapter and registry
entry. Reasoning services consume the provider-agnostic contract.

## Configuration

```txt
LLM_REASONING_ENABLED=false
LLM_DEFAULT_PROVIDER=mock
LLM_DEFAULT_MODEL=mock-scenario-v1
LLM_PROVIDER_TIMEOUT_SECONDS=12
LLM_MAX_OUTPUT_TOKENS=450
LLM_TEMPERATURE=0.2
OPENAI_API_KEY=
OPENAI_BASE_URL=
ANTHROPIC_API_KEY=
LLM_STORE_INPUTS=false
LLM_STORE_OUTPUTS=true
```

Real provider keys are optional at startup. Tests use `mock` and make no external calls.

## Persistence

Reasoning runs are stored in `llm_reasoning_runs`. Individual scenarios are stored in
`scenario_hypotheses`.

Run statuses include `pending`, `completed`, `failed`, `blocked`, `fallback_used`, and
`provider_not_configured`. Safety status and grounding status are persisted separately for audit.

## Prompt And Output

Prompt version: `scenario_reasoning_v1`.

The prompt instructs the model to use only supplied facts, avoid signal classification or overrides,
avoid invented evidence, avoid causation claims, avoid trading advice, and return strict JSON:

```json
{
  "summary": "string",
  "scenarios": [
    {
      "scenarioType": "continuation",
      "scenarioLabel": "string",
      "possibilityLabel": "medium",
      "supportingEvidence": ["string"],
      "conflictingEvidence": ["string"],
      "outcomeHistory": {"available": true, "summary": "string"},
      "nextObservations": ["string"],
      "suggestedBackendActions": ["evaluate_outcome_after_horizon"],
      "riskNotes": ["string"]
    }
  ],
  "limitations": ["string"]
}
```

Allowed backend actions are:

- `evaluate_outcome_after_horizon`
- `run_replay`
- `run_news_correlation`
- `wait_for_more_final_candles`
- `request_human_review`
- `no_action`

## Safety And Grounding

Safety blocks direct trade instructions and prohibited claims such as buy/sell-now language,
position-change instructions, margin instructions, order placement, certainty claims, impossible-risk claims, and
certain future direction claims.

Grounding blocks output that mentions patterns or strategy profiles not in input, numeric values not
present in input, news when no news correlation exists, news causation claims, disallowed backend
actions, certain future scenarios, or invented outcome history.

Blocked or ungrounded output is not exposed. The service stores fallback scenario hypotheses that
direct the caller to review deterministic artifacts or request human review.

## APIs

```txt
POST /signals/{signal_id}/reasoning/scenarios
GET /signals/{signal_id}/reasoning/runs
GET /signals/{signal_id}/reasoning/scenarios/latest
GET /reasoning/runs/{reasoning_run_id}
```

Generation is manual only. The analysis lifecycle does not automatically invoke scenario reasoning.
