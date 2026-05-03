# Notifications

The notification system has two backend-only layers:

- existing user notification outbox for in-app operational messages
- notification delivery engine for sanitized backend intelligence events

Neither layer is a trading alert engine, broker workflow, order system, auto-trading path, or
financial-advice channel.

## Channels

Delivery channels are stored in `notification_channels`.

Supported channel types:

```txt
webhook
email
telegram
discord
```

Supported channel statuses:

```txt
active
paused
archived
```

Channel config is provider-specific and must not contain inline secrets. Use `secret_ref` for
future secret resolution. Active channels can filter event types, severity, and quiet hours.

## Event Types

Delivery events are stored in `notification_events`.

Supported event types:

```txt
signal.classified
signal.review_recommended
outcome.evaluated
digest.created
data_quality.degraded
market_memory.stale
reasoning.action_due
readiness.blocked
operator_review.opened
```

`digest.created` events are not created or delivered automatically by digest generation. They must
be created explicitly through the notification event API and delivered explicitly through the
delivery API.

Supported severities:

```txt
info
low
medium
high
critical
```

Supported event statuses:

```txt
pending
held
delivered
partially_delivered
blocked
cancelled
failed
```

## Safety Filtering

Before an event is persisted for delivery, the service sanitizes its title, summary, and payload.

The safety layer:

- blocks direct trading instruction and financial-advice language
- redacts secrets, credentials, tokens, and authorization fields
- removes raw candle series and raw chart image payloads
- removes unsafe LLM output fields
- truncates payloads to `NOTIFICATION_MAX_PAYLOAD_BYTES`
- stores safety status and redaction metadata in the event payload

Deliverable payloads must not contain broker instructions, order instructions, raw candles, raw
images, secrets, unsafe LLM output, or trade-advice language.

## Dedupe

The default dedupe key is built from:

```txt
workspace_id + event_type + source_type + source_id + severity
```

If an event with the same key was delivered, partially delivered, or held inside
`NOTIFICATION_DEDUPE_WINDOW_SECONDS`, creating a duplicate returns the existing event.

## Quiet Hours

Channels can define quiet hours with:

```json
{
  "enabled": true,
  "timezone": "UTC",
  "start": "22:00",
  "end": "07:00",
  "behavior": "hold"
}
```

`behavior` can be `hold` or `skip`. Quiet hours are evaluated at delivery time. This phase does not
schedule a later external delivery worker for held events.

## Delivery Adapters

`webhook` performs a real HTTP POST when:

- `NOTIFICATIONS_ENABLED=true`
- the event is explicitly delivered
- the channel is active
- the channel matches event type and severity filters
- quiet hours allow delivery
- `config_json.target_url` or `config_json.url` is configured

`email`, `telegram`, and `discord` are production-shaped safe stubs. They validate expected
configuration shape and record skipped attempts until secret resolution and provider-specific
sending are implemented.

No adapter sends messages during startup or tests.

## APIs

Channel APIs:

```txt
POST /notification-channels
GET /notification-channels
GET /notification-channels/{channel_id}
PATCH /notification-channels/{channel_id}
POST /notification-channels/{channel_id}/archive
```

Event APIs:

```txt
POST /notification-events
GET /notification-events
GET /notification-events/{event_id}
POST /notification-events/{event_id}/deliver
GET /notification-events/{event_id}/attempts
```

Existing in-app notification APIs remain available:

```txt
PUT /notifications/preferences
GET /notifications/preferences
POST /notifications
GET /notifications
GET /notifications/{notification_id}
POST /notifications/{notification_id}/read
POST /notifications/dispatch-due
GET /notifications/worker/status
```

## Settings

```txt
NOTIFICATIONS_ENABLED=false
NOTIFICATION_DELIVERY_TIMEOUT_SECONDS=10
NOTIFICATION_MAX_PAYLOAD_BYTES=16000
NOTIFICATION_DEDUPE_WINDOW_SECONDS=3600
NOTIFICATION_DEFAULT_QUIET_HOURS_TIMEZONE=UTC
NOTIFICATION_WEBHOOK_USER_AGENT=trading-intelligence-notifications/0.1
```

Existing worker settings still control the legacy in-app notification worker.

## Safety Boundaries

The notification engine does not:

- create UI
- execute broker actions
- place orders
- auto-trade
- send trade advice
- include raw candles or raw chart images
- include secrets or unsafe LLM output
- send external messages unless configured and explicitly invoked
