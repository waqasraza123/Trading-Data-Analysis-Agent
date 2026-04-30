# Notifications

The notification system is an operator-facing outbox for backend events. It is not a trading alert,
broker workflow, order system, or financial-advice channel.

## Scope

Notifications can record and dispatch safe operational messages such as:

```txt
signal_ready
analysis_completed
human_review_requested
outcome_ready
diagnostic_ready
ai_intelligence_ready
system_health
manual_operator_note
```

Messages are persisted in `notification_messages` with source metadata, severity, delivery status,
idempotency key, attempts, leases, result payload, and read state. Preferences are persisted in
`notification_preferences` per workspace, user, channel, and event type.

## Delivery

Current delivery support:

```txt
in_app
```

`email` and `webhook` are modeled as future channels but are not externally sent yet. If queued,
dispatch marks them failed with `notification_channel_not_configured` rather than pretending they
were delivered.

Notification content runs through the same safety language checks used by explanation layers.
Messages containing direct trade instructions, guarantees, or leverage language are rejected.

## APIs

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

`POST /notifications/dispatch-due` is safe for manual operation and processes due queued messages
through the same service used by the worker.

## Worker

Run the worker with:

```sh
NOTIFICATION_WORKER_ENABLED=true .venv/bin/python -m app.workers.notification_worker
```

Worker settings:

```txt
NOTIFICATION_WORKER_ENABLED=false
NOTIFICATION_WORKER_POLL_SECONDS=10
NOTIFICATION_WORKER_BATCH_SIZE=100
NOTIFICATION_WORKER_LOCK_SECONDS=120
NOTIFICATION_WORKER_MAX_ATTEMPTS=3
NOTIFICATION_WORKER_JITTER_SECONDS=2
```

The worker claims queued messages with database leases and retries only while attempts remain under
the configured limit.
