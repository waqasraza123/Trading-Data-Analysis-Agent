# Grounded AI Intelligence Analyst

The AI intelligence module generates persisted, advisory operator insights from existing backend
artifacts. It uses the existing LLM adapter layer, but every output must be grounded in supplied
artifact references from read-only intelligence reports.

It is not a chatbot, classifier, broker workflow, auto-trading system, alert system, or financial
advice path.

## Endpoints

```txt
POST /ai-intelligence/signals/{signal_id}/analyze
GET /ai-intelligence/runs/{run_id}
GET /ai-intelligence/signals/{signal_id}/runs
```

## Settings

```txt
AI_INTELLIGENCE_ENABLED=false
AI_INTELLIGENCE_MAX_OUTPUT_TOKENS=700
```

Provider/model selection uses the existing LLM adapter settings by default:

```txt
LLM_DEFAULT_PROVIDER=mock
LLM_DEFAULT_MODEL=mock-scenario-v1
LLM_PROVIDER_TIMEOUT_SECONDS=12
LLM_TEMPERATURE=0.2
```

## Stored Records

`ai_intelligence_runs` stores the subject, provider/model, prompt version, safety status, grounding
status, token/cost metadata, input snapshot policy, and output metadata.

`ai_intelligence_insights` stores bounded advisory insight cards with type, severity, title,
summary, rationale, cited evidence references, limitations, and safe backend follow-up action names.

`ai_intelligence_claims` stores claim-level text with support status and evidence references.

## Grounding

The input snapshot is built from the existing read-only intelligence report for a signal. The module
collects artifact references such as signal, analysis run, action plan, outcome, reasoning run, news
event, screenshot run, diagnostic run, symbol, and data source IDs.

The parser requires every insight and claim to cite supplied artifact references. Unknown or missing
citations fail grounding and trigger a safe fallback record instead of accepting unsupported output.

## Safety

The analyst may identify evidence consistency, confidence alignment, historical outcome context,
diagnostic context, news context, data gaps, action-plan state, risk context, and human-review
context.

It must not:

```txt
classify signals
override deterministic signals
invent evidence, prices, indicators, outcomes, or news
claim news causation
recommend buy/sell/enter/exit actions
place orders or manage positions
create executable action items
auto-tune strategy profiles
produce alerts or notifications
claim certain behavior
```

Safe follow-up action names are advisory only. They do not create action items and they do not
execute backend work.

## Operational Notes

The module is disabled by default. When disabled or when a provider is unavailable, it stores a
fallback run explaining that persisted deterministic artifacts should be reviewed directly.

Mock provider output is deterministic and useful for local tests. Production providers require the
existing provider credentials and should be enabled deliberately.
