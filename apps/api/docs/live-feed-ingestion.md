# Live Feed Ingestion Foundation

This slice adds the backend foundation for live market data ingestion. A persistent worker
foundation exists for polling active subscriptions and handling provider reconnects, but this
backend does not trigger broker execution, alerts, news correlation, UI, or LLM calls.

## Boundary

Live feed ingestion uses the same candle truth table as historical imports:

```txt
provider payload
-> live provider adapter
-> live_feed_events audit row
-> NormalizedCandleInput
-> shared candle validator
-> shared candle repository
-> candles
```

The analysis engine must not care whether candles came from CSV, JSON import, Binance, mock live data, or another provider.

## Implemented Modules

```txt
app/modules/live/
  heartbeat.py
  models.py
  repository.py
  routes.py
  schemas.py
  service.py
  providers/
    base.py
    binance.py
    mock.py
    registry.py
```

## Provider Abstraction

Every provider adapter exposes:

```txt
connect()
disconnect()
subscribe(symbol, timeframe)
unsubscribe(symbol, timeframe)
handle_message(payload)
normalize_message(payload)
```

The current adapters are:

```txt
mock
binance
```

`mock` is intended for local development, API clients, and future tests.

`binance` currently normalizes Binance kline payloads into internal candle events. It does not open websocket connections yet.

## Subscription APIs

```txt
POST /live/subscriptions
GET /live/subscriptions
GET /live/subscriptions/{subscription_id}
PATCH /live/subscriptions/{subscription_id}
POST /live/subscriptions/{subscription_id}/pause
POST /live/subscriptions/{subscription_id}/resume
POST /live/subscriptions/{subscription_id}/stop
POST /live/subscriptions/stale-check
```

Subscriptions require:

```txt
active symbol
active data source
data source type websocket_live
data source workspace matching subscription workspace
supported provider
supported timeframe
```

## Event APIs

```txt
POST /live/subscriptions/{subscription_id}/events
GET /live/subscriptions/{subscription_id}/events
```

The POST endpoint is an internal ingestion boundary for provider messages. It stores raw event payloads in `live_feed_events` before normalizing candles.

Example mock partial candle event:

```json
{
  "eventType": "candle_partial",
  "providerTimestamp": "2026-04-29T10:00:10Z",
  "payloadJson": {
    "candle": {
      "timestamp": "2026-04-29T10:00:00Z",
      "open": "65000.00",
      "high": "65040.00",
      "low": "64980.00",
      "close": "65025.00",
      "volume": "12.50"
    }
  }
}
```

Example mock final candle event:

```json
{
  "eventType": "candle_final",
  "providerTimestamp": "2026-04-29T10:01:00Z",
  "payloadJson": {
    "candle": {
      "timestamp": "2026-04-29T10:00:00Z",
      "open": "65000.00",
      "high": "65050.00",
      "low": "64980.00",
      "close": "65040.00",
      "volume": "18.20"
    }
  }
}
```

## Candle Upsert Rules

Live candles use the existing candle repository behavior:

```txt
partial candle inserted when timestamp is new
partial candle updated when timestamp already has a partial row
final candle replaces a partial row
late partial candle is ignored after a final row exists
duplicate final candle is accepted as duplicate
conflicting final candle marks the live event failed
```

`live_feed_event_id` links the candle row to the most recent live event that created or updated it.

## Audit Behavior

Every provider message creates a `live_feed_events` row with:

```txt
workspace_id
source_id
subscription_id
provider
event_type
received_at
provider_timestamp
payload_json
processing_status
error_message
```

Provider payload failures are stored as failed live events when a subscription can be resolved.

Provider `error` messages mark the subscription failed and preserve the provider error.

Paused or stopped subscriptions store incoming events as ignored.

## Stale Detection

`POST /live/subscriptions/stale-check` marks active subscriptions stale when:

```txt
last message is older than message_stale_after_seconds
or
last final candle is older than final_candle_stale_after_seconds
```

Defaults:

```txt
message_stale_after_seconds = 180
final_candle_stale_after_seconds = 300
```

These thresholds can be supplied per stale-check request.

## Worker Runtime

```txt
python -m app.workers.live_feed_worker
python -m app.workers.live_stale_monitor
```

The live worker polls active subscriptions, acquires database leases, streams provider messages
through the provider abstraction, and writes events through `LiveService.ingest_provider_message`.
The stale monitor refreshes stale subscription status using the same service boundary.

Operational details are documented in:

```txt
docs/live-runtime.md
```

## Not Implemented In This Slice

```txt
Redis-backed worker orchestration
scheduled live scanner
LLM explanations
news correlation
broker execution
UI
```

## Operational Notes

- Use `websocket_live` data sources for live subscriptions.
- Use `mock` provider for local ingestion flows.
- Use `binance` only for Binance kline payload normalization until a worker owns websocket lifecycle.
- The API accepts live events synchronously, but future workers should call the same `LiveService.ingest_provider_message` boundary.
- Do not write live candles directly to the candle table from provider workers.
