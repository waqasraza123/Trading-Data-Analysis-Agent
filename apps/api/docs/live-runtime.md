# Live Runtime Operations

The live runtime consumes active live subscriptions and writes provider messages through the same
`LiveService.ingest_provider_message` boundary used by the API.

## Processes

Run the subscription worker:

```sh
cd apps/api
python -m app.workers.live_feed_worker
```

Run the stale monitor:

```sh
cd apps/api
python -m app.workers.live_stale_monitor
```

Both require `DATABASE_URL`.

## Runtime Settings

```txt
LIVE_FEED_PROVIDER=
LIVE_FEED_API_KEY=
LIVE_FEED_RECONNECT_INITIAL_SECONDS=1
LIVE_FEED_RECONNECT_MAX_SECONDS=60
LIVE_FEED_RECONNECT_MULTIPLIER=2
LIVE_FEED_STALE_MESSAGE_SECONDS=180
LIVE_FEED_STALE_FINAL_CANDLE_SECONDS=300
LIVE_FEED_WORKER_POLL_SECONDS=10
```

`LIVE_FEED_API_KEY` is optional unless the selected provider requires a key.

## Worker Behavior

- The live worker generates a worker id on startup.
- Subscription leases are refreshed while a stream is active.
- Provider disconnects use bounded exponential reconnect delays.
- Poll loop failures are logged and the worker keeps polling.
- Subscription stream failures mark the subscription failed without logging secrets.
- `SIGINT` and `SIGTERM` trigger graceful shutdown.
- Startup and shutdown emit `worker_started`, `worker_stopped`, `live_worker_started`, and
  `live_worker_stopped`.

## Stale Monitor Behavior

The stale monitor periodically calls the existing stale status service. It emits
`stale_monitor_started`, `stale_monitor_stopped`, and `live_subscription_stale` events.

## Health

```txt
GET /health/workers
```

The endpoint reports database state, live worker status, stale monitor availability, and Redis
configuration state. The API readiness endpoint does not require the live worker to be running.

## Still Not Implemented

This runtime does not add broker execution, auto-trading, alerts, news correlation, UI, copy/social
trading, or LLM calls.
