# Webhook Outbox

The webhook outbox records sanitized backend intelligence events for future integrations. It is an auditable persistence layer only.

It does not send HTTP requests, deliver alerts, notify users, execute broker actions, create orders, copy trades, or provide financial advice.

## Pattern

Subscriptions describe future destinations and event type interest:

```txt
webhook_subscriptions
```

Outbox records store one prepared payload for a backend artifact:

```txt
webhook_outbox_events
```

Delivery attempts are modeled for a later delivery phase:

```txt
webhook_delivery_attempts
```

This phase creates subscriptions and outbox events only. There is no worker and no network transmission path.

## Event Types

Allowed event types:

```txt
signal.classified
outcome.evaluated
reasoning.scenarios_generated
action_plan.created
action_item.completed
action_item.failed
quality.finding_created
readiness.blocked
operator_review.opened
```

Supported source types by event:

```txt
signal.classified: signal
outcome.evaluated: outcome
reasoning.scenarios_generated: reasoning_run
action_plan.created: action_plan
action_item.completed: action_item
action_item.failed: action_item
quality.finding_created: strategy_profile_diagnostic, pattern_outcome_diagnostic, calibration_recommendation
readiness.blocked: analysis_run, screenshot_decision, action_item
operator_review.opened: action_item, screenshot_decision
```

## Safe Payloads

Payloads include IDs, statuses, labels, summaries, safe metrics, bounded evidence, and internal API paths when available.

Payloads do not include:

```txt
secrets
signing secret plaintext
raw images
raw candle series
unsafe blocked LLM output
trade instructions
broker order fields
copy-trading instructions
financial advice
```

Signing material is represented only by `signingSecretRef` on subscriptions. The referenced secret is not stored in the database by this module.

## Redaction

The payload builder recursively sanitizes generated payloads before persistence.

It redacts secret-like keys, raw image fields, full candle-series fields, unsafe LLM output fields, and text containing direct order, position, margin, or risk-management instruction language.

Redaction decisions are stored in `redaction_warnings_json` on the outbox event.

## API

```txt
POST /webhook-subscriptions
GET /webhook-subscriptions
GET /webhook-subscriptions/{subscription_id}
PATCH /webhook-subscriptions/{subscription_id}
POST /webhook-subscriptions/{subscription_id}/archive
POST /webhook-outbox/events
GET /webhook-outbox/events
GET /webhook-outbox/events/{event_id}
POST /webhook-outbox/events/{event_id}/cancel
```

Create outbox event:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "eventType": "signal.classified",
  "sourceType": "signal",
  "sourceId": "00000000-0000-0000-0000-000000000000"
}
```

Outbox events default to `held`. A caller may explicitly request `pending`, but this phase still does not deliver it.

## Subscription Status

```txt
active
paused
archived
```

Archived subscriptions cannot be updated or receive new outbox records.

## Outbox Status

```txt
pending
held
cancelled
delivered
failed
```

Only `pending` and `held` can be used when creating records in this phase. Only `pending` and `held` records can be cancelled.

## Not Implemented

The following are intentionally excluded:

```txt
delivery worker
HTTP client
retry scheduler
signature generation
external alert delivery
user notification delivery
broker execution
auto-trading
copy trading
financial advice
```
