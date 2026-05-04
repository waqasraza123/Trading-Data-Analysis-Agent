# Safety Policy Engine

The Safety Policy Engine centralizes backend safety checks for market-intelligence output. It is additive and does not replace existing deterministic explanation, LLM explanation, reasoning, scenario ensemble, action plan, report, dataset, webhook outbox, operator playbook, or decision-readiness checks yet.

## Policy Set

The default policy set is `core_market_intelligence` version `v1`.

It includes:

- blocked trading actions
- unsafe direct phrases
- causation phrases
- invented evidence phrases
- secret key indicators
- prohibited output claims
- provider payload exposure keys

Policy sets are stored in `safety_policy_sets` and can be workspace-scoped or global.

## Evaluation Types

Supported evaluation types are:

- `text`
- `action`
- `payload`
- `report`
- `reasoning_output`
- `webhook_payload`
- `dataset_record`

Evaluation records are stored in `safety_policy_evaluations`.

## Action Blocking

The engine blocks direct trading execution actions such as `buy`, `sell`, `place_order`, `execute_trade`, `copy_trade`, `use_leverage`, `open_position`, and `close_position`.

This does not add broker execution, auto-trading, copy trading, alerts, notifications, or financial advice. It only centralizes rejection logic so future modules can call one policy layer.

## Language Safety

Unsafe direct order instructions, certainty claims, and impossible-risk claims are blocked.

Causation phrases such as `definitely caused`, `confirmed cause`, and `caused the move` are flagged for review. Neutral market-language terms such as bullish pressure or bearish behavior are not blocked by default.

Invented or ungrounded evidence phrases such as `data proves`, `evidence proves`, and `source confirms` are flagged for review so public explanations do not imply stronger grounding than the system has verified.

## Redaction

Payload redaction preserves object shape where possible and replaces sensitive field values with `[REDACTED]`.

Sensitive keys include:

- `api_key`
- `token`
- `secret`
- `password`
- `database_url`
- `authorization`
- `credential`
- `private_key`

Public payload evaluations also redact provider-internal payload keys such as raw provider payloads, prompts, messages, and raw responses.

## API Contracts

`GET /safety-policies`

Lists stored policy sets.

`GET /safety-policies/{key}/{version}`

Returns a stored policy set.

`POST /safety-policies/seed-default`

Seeds `core_market_intelligence` `v1`.

`POST /safety-policies/evaluate-text`

```json
{
  "workspaceId": null,
  "text": "..."
}
```

`POST /safety-policies/evaluate-action`

```json
{
  "workspaceId": null,
  "action": "place_order"
}
```

`POST /safety-policies/evaluate-payload`

```json
{
  "workspaceId": null,
  "payload": {
    "token": "secret-value"
  },
  "publicResponse": true
}
```

Responses include:

- `policySetKey`
- `policySetVersion`
- `evaluationType`
- `status`
- `safetyStatus`
- `findings`
- `inputSummaryJson`
- `redactedOutputJson`

Findings include:

- `code`
- `severity`
- `message`
- `matchedValue`
- `location`

## Future Adoption Path

Adopt the service incrementally from low-risk backend modules first:

1. Public response sanitization and report output.
2. Reasoning and LLM explanation post-processing.
3. Dataset record ingestion and webhook outbox payload checks.
4. Operator playbooks and decision-readiness gates.
5. Existing deterministic safety checks after parity tests are added.
