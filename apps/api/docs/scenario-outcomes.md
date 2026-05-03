# Scenario Hypothesis Outcome Tracker

Scenario hypothesis outcome tracking closes the loop on persisted scenario reasoning. It evaluates whether stored scenario hypotheses were later supported, contradicted, or remained inconclusive by comparing them with stored `signal_outcomes`.

This is reasoning QA only. It is not prediction, trading performance, financial advice, broker execution, auto-trading, alerts, UI behavior, or LLM generation.

## Safety Boundary

The tracker:

- reads persisted `scenario_hypotheses`, `llm_reasoning_runs`, `signal_outcomes`, and stored news correlations
- writes separate `scenario_hypothesis_outcomes` rows
- writes aggregate `scenario_outcome_summary_runs` rows
- does not mutate scenario hypotheses, signals, outcomes, news correlations, or action plans
- does not call LLM providers
- does not inspect candles directly
- does not create alerts, recommendations, broker actions, or trading advice

If a stored signal outcome is missing for the requested horizon, the scenario outcome row is marked `insufficient_outcome_data`.

## Persistence

`scenario_hypothesis_outcomes` stores one deterministic evaluation per hypothesis, horizon, and evaluation version:

- hypothesis, reasoning run, signal, analysis run, and outcome pointers
- scenario type and possibility label copied from the hypothesis
- evaluation status
- support label and support score
- matched outcome label
- matched and conflicting evidence
- deterministic summary

`scenario_outcome_summary_runs` stores workspace-scoped aggregate counts over existing scenario outcome rows and optional filters.

## Settings

```txt
SCENARIO_OUTCOME_EVALUATION_VERSION=v1
SCENARIO_OUTCOME_DEFAULT_HORIZON_MINUTES=30
SCENARIO_OUTCOME_SUPPORT_THRESHOLD=0.6000
```

## Mapping Rules

The evaluator maps persisted scenario types to existing `signal_outcomes.outcome_label` values:

- `continuation`: `continuation` supports; `partial_follow_through` partially supports; reversal or no-follow-through labels contradict.
- `reversal`: `reversal` supports; continuation labels contradict; no-follow-through and sideways labels remain inconclusive.
- `consolidation`: `no_follow_through` or `sideways_after_signal` supports; directional continuation or reversal contradicts.
- `volatility_expansion`: requires stored elevated volatility metadata or movement context; otherwise inconclusive.
- `fakeout_risk`: reversal or no-follow-through supports when breakout context is stored or implied by the scenario label; without breakout context it is partially supported.
- `event_driven_volatility`: requires possible or strong news correlation with elevated or spike volatility reaction plus elevated volatility outcome context.
- `insufficient_context`: not applicable.

The evaluator uses stored `signal_outcomes` only. It does not compute new outcomes or read candles.

## API

```txt
POST /reasoning/scenarios/{scenario_hypothesis_id}/outcome
POST /reasoning/runs/{reasoning_run_id}/scenario-outcomes
GET /reasoning/runs/{reasoning_run_id}/scenario-outcomes
POST /scenario-outcomes/summary
GET /scenario-outcomes/summary/{summary_run_id}
```

Single hypothesis request:

```json
{
  "horizonMinutes": 30,
  "forceRecompute": false
}
```

Reasoning-run request:

```json
{
  "horizonsMinutes": [30, 60],
  "forceRecompute": false
}
```

Summary request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "filters": {
    "scenarioType": "continuation",
    "supportLabel": "supported",
    "provider": "mock",
    "horizonMinutes": 30
  }
}
```

## Status Labels

Evaluation statuses:

- `evaluated`
- `insufficient_outcome_data`
- `not_applicable`
- `failed`

Support labels:

- `supported`
- `partially_supported`
- `contradicted`
- `inconclusive`
- `not_applicable`

Summary run statuses:

- `pending`
- `completed`
- `completed_with_warnings`
- `failed`

## Historical Reliability Use

Summary runs let operators inspect which scenario types, providers, and persisted reasoning runs were often supported or contradicted after outcomes existed. This is reliability analysis of reasoning artifacts, not signal performance or trading PnL.
