# Grounded LLM Explanations

This optional layer generates clearer analysis text from persisted deterministic artifacts. It does not classify signals, change signal output, invent market values, recommend trades, or call a broker.

## Boundary

The LLM reads only the grounded payload assembled from:

```txt
signal
analysis run
symbol and timeframe
strategy profile snapshot
feature snapshot
indicator snapshot
confidence components
signal evidence
risk notes
deterministic explanation
movement fields
optional persisted news correlations with safe event summary fields only
```

It does not receive raw full candle datasets, raw news provider payloads, secrets, database URLs,
unrelated user/workspace data, stack traces, or provider responses.

## Settings

```txt
LLM_EXPLANATIONS_ENABLED=false
LLM_PROVIDER=mock
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=12
LLM_MAX_INPUT_TOKENS=1800
LLM_MAX_OUTPUT_TOKENS=450
OPENAI_API_KEY=
LLM_STORE_INPUTS=false
LLM_STORE_OUTPUTS=true
```

`OPENAI_API_KEY` is optional at API startup. It is required only when `LLM_EXPLANATIONS_ENABLED=true` and `LLM_PROVIDER=openai`.

## Providers

`mock` is the default provider and is intended for tests and local deterministic behavior.

`openai` uses the OpenAI Responses API through a thin optional wrapper. No OpenAI package dependency is required; the wrapper uses the standard library and does not log raw responses or secrets.

## Safety And Grounding

The prompt requires the model to explain only supplied facts, avoid financial advice, avoid buy/sell/enter/exit language, avoid guarantees, mention uncertainty and risk notes, and include:

```txt
This is analysis based on available backend data, not a trade instruction.
```

Safety blocks direct order instructions, certainty claims, impossible-risk claims, margin instructions, and directive position language.

When news correlations exist, the LLM input includes only event title, event type, event time,
currency/asset, importance, correlation label, score, time delta, direction/volatility reaction,
and cautious reason. If no persisted correlation exists, the prompt explicitly forbids mentioning
news, events, announcements, or headlines.

Grounding checks flag invented numeric values, unsupported pattern mentions, news/event mentions
without persisted news correlation input, news/event mentions that do not match persisted event
descriptors, direct order instruction language, news causation claims, and certainty claims.

If output is unsafe or clearly ungrounded, the API returns and persists deterministic fallback text instead of unsafe model text.

## API

```txt
POST /signals/{signal_id}/llm-explanation
GET /signals/{signal_id}/llm-explanation
POST /analysis-runs/{analysis_run_id}/llm-explanation
GET /analysis-runs/{analysis_run_id}/llm-explanation
```

Signal responses include `llmExplanation` when a row exists.

## Lifecycle

When `include_ai_explanation=true`, the analysis lifecycle attempts grounded LLM explanation
generation after deterministic explanation generation. When both `include_news_correlation=true`
and `include_ai_explanation=true`, news correlation runs first so the LLM can include only persisted
correlation context. Provider failures, missing keys, disabled settings, safety blocks, and grounding
failures use fallback text and do not fail the analysis run.

Audit events include:

```txt
llm_explanation_requested
llm_explanation_input_built
llm_explanation_generated
llm_explanation_blocked
llm_explanation_grounding_failed
llm_explanation_fallback_used
llm_explanation_failed
llm_explanations_calculated
```
