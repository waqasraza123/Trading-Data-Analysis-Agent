# Go Market Data Worker

This service is an additive market data sidecar for the existing Python/Postgres platform.
Python remains the canonical API, orchestration, auth/RBAC, migrations, deterministic
intelligence, LLM/reporting, and UI contract layer.

The Go worker only handles backend worker execution for provider polling, candle normalization,
batch candle writes, provider health snapshots, runtime heartbeat, and operational health metrics.
It does not place orders, connect to brokers for execution, send alerts, classify signals, run LLMs,
mutate strategy profiles, or replace FastAPI.

## Run Locally

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
go run ./cmd/market-worker
```

Run one bounded claim/process pass:

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=once \
go run ./cmd/market-worker
```

Inspect database compatibility without claiming work:

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=inspect \
go run ./cmd/market-worker
```

Health endpoints:

```txt
GET http://127.0.0.1:8091/healthz
GET http://127.0.0.1:8091/readyz
GET http://127.0.0.1:8091/metrics.json
```

`/readyz` and inspect mode include required and optional column problems so operators can catch
schema drift before enabling the worker. `/metrics.json` includes provider gate wait counters so
operators can see whether provider backpressure is active.

## Configuration

Required:

- `DATABASE_URL`

Optional:

- `MARKET_WORKER_ID`
- `MARKET_WORKER_QUEUE_NAME`, default `market-data`
- `MARKET_WORKER_POLL_SECONDS`, default `5`
- `MARKET_WORKER_BATCH_SIZE`, default `10`
- `MARKET_WORKER_MAX_CONCURRENCY`, default same as `MARKET_WORKER_BATCH_SIZE`
- `MARKET_WORKER_PROVIDER_MAX_CONCURRENCY`, default same as `MARKET_WORKER_BATCH_SIZE`
- `MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS`, default `0`
- `MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD`, default `5`
- `MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS`, default `60`
- `MARKET_WORKER_JOB_LOCK_SECONDS`, default `120`
- `MARKET_WORKER_JOB_TIMEOUT_SECONDS`, default `300`
- `MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS`, default `15`
- `MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS`, default same as `MARKET_WORKER_JOB_TIMEOUT_SECONDS`
- `MARKET_WORKER_PROVIDER_TIMEOUT_SECONDS`, default `20`
- `MARKET_WORKER_MAX_CANDLES_PER_REQUEST`, default `1000`
- `MARKET_WORKER_HEALTH_ADDR`, default `:8091`
- `MARKET_WORKER_LOG_LEVEL`, default `info`
- `MARKET_WORKER_MODE`, default `jobs`
- `MARKET_WORKER_RUN_MODE`, default `serve`
- `MARKET_WORKER_RETRY_BACKOFF_SECONDS`, default `60`
- `BINANCE_PUBLIC_REST_BASE_URL`, default `https://api.binance.com`
- `MARKET_WORKER_ENABLE_LIVE_STREAM`, default `true`
- `MARKET_WORKER_BINANCE_LIVE_WS_BASE_URL`, default `wss://stream.binance.com:9443/ws`
- `MARKET_WORKER_LIVE_STREAM_CLAIM_INTERVAL_SECONDS`, default `5`
- `MARKET_WORKER_LIVE_STREAM_CLAIM_BATCH_SIZE`, default same as `MARKET_WORKER_BATCH_SIZE`
- `MARKET_WORKER_LIVE_STREAM_LEASE_SECONDS`, default `90`
- `MARKET_WORKER_LIVE_STREAM_RECONNECT_SECONDS`, default `5`
- `MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_SECONDS`, default `60`
- `MARKET_WORKER_LIVE_STREAM_RECONNECT_JITTER_PERCENT`, default `20`
- `MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_ATTEMPTS`, default `12`
- `MARKET_WORKER_LIVE_STREAM_READ_TIMEOUT_SECONDS`, default `30`
- `MARKET_WORKER_LIVE_STREAM_MESSAGE_BUFFER`, default `64`
- `MARKET_WORKER_LIVE_STREAM_MAX_MESSAGE_PARSE_FAILURES`, default `0` (unbounded)
- `MARKET_WORKER_LIVE_STREAM_MESSAGE_STALE_SECONDS`, default `180`
- `MARKET_WORKER_LIVE_STREAM_FINAL_STALE_SECONDS`, default `300`
- `MARKET_WORKER_LIVE_STREAM_GAP_RECOVERY`, default `true`
- `MARKET_WORKER_LIVE_STREAM_GAP_REQUEST_LIMIT`, default `1000`
- `MARKET_WORKER_ENABLE_LIVE_BINANCE`, default `true`
- `MARKET_WORKER_ENABLE_BINANCE_PUBLIC`, default `true`
- `MARKET_WORKER_ENABLE_MOCK_PROVIDER`, default `true`

The worker does not require Redis, LLM keys, OCR keys, broker credentials, or external provider
credentials at startup.

## Run Modes

- `serve`: long-running worker with health endpoints, DB heartbeat when available, and periodic job claiming.
- `once`: claim and process one bounded batch, then exit.
- `inspect`: connect to Postgres, detect table and column capabilities, print JSON, and exit without claiming work.

`MARKET_WORKER_BATCH_SIZE` controls how much work one claim cycle can reserve. `MARKET_WORKER_MAX_CONCURRENCY`
controls how many claimed jobs or direct polling requests execute at the same time. Keep concurrency below the
database connection pool and provider rate-limit budget.

Live processing is optional in `jobs` mode and requires compatible `live_feed_subscriptions` and
`live_feed_events` tables:

- `MARKET_WORKER_ENABLE_LIVE_STREAM` toggles the runtime consumer.
- `MARKET_WORKER_LIVE_STREAM_CLAIM_INTERVAL_SECONDS` controls claim polling frequency.
- `MARKET_WORKER_LIVE_STREAM_CLAIM_BATCH_SIZE` controls max active subscriptions per claim cycle.
- `MARKET_WORKER_LIVE_STREAM_LEASE_SECONDS` controls lease TTL and heartbeat cadence.
  Lease renewal health is exposed in `/metrics.json`:
  - `liveLeaseRenewals`
  - `liveLeaseRenewalFailures`
  - `liveLeaseLost`
  - `liveLeaseAcquisitionMisses`
  - `liveLeaseReleaseFailures`
  - `liveSubscriptionRunsCompleted`
  - `liveSubscriptionRunsFailed`
  - `liveSubscriptionRunsParseThresholdExceeded`
  - `liveSubscriptionStartupLoadFailures`
  - `liveMessageParseFailures`
  - `liveMessageParseThresholdExceeded`
  - `liveCandlesWritten`
  - `liveMessageDrops`
  Status transitions are reflected by `liveSubscriptionsStopped` when an active subscription is
  externally moved to `paused`, `failed`, or `stopped`.
- `MARKET_WORKER_ENABLE_LIVE_BINANCE`, `MARKET_WORKER_LIVE_STREAM_RECONNECT_SECONDS`, and
  `MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_SECONDS` control websocket reconnect behavior.
  Reconnect delay uses exponential backoff in seconds from the base value up to the max cap and
  optional jitter through `MARKET_WORKER_LIVE_STREAM_RECONNECT_JITTER_PERCENT` to reduce retry
  synchronization across workers.
- `MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_ATTEMPTS` controls consecutive reconnect attempts before
  marking a subscription as `failed` to avoid unbounded reconnect storms.
- Provider error frames now terminate the current live stream for that subscription immediately after the
  subscription status is moved to `failed`; no reconnect loop is executed.
- `MARKET_WORKER_LIVE_STREAM_READ_TIMEOUT_SECONDS` controls websocket read deadline behavior; repeated read
  timeouts increment `liveReconnectReadTimeouts` in `/metrics.json` and trigger the same bounded
  reconnect policy.
- `MARKET_WORKER_LIVE_STREAM_MAX_MESSAGE_PARSE_FAILURES` controls how many consecutive stream parse failures
  are tolerated before the worker marks a subscription as `failed` and ends the stream loop for that subscription.
  Set `0` to disable parse-based hard stop.
- Terminal subscription failures (`provider errors`, `message parse threshold exhaustion`, and initial startup
  configuration issues like missing/invalid provider symbol/timeframe) are marked `failed` even if
  `live_feed_events` persistence is unavailable so status transitions remain deterministic in trimmed
  compatibility schemas.
- The worker now also hard-fails subscriptions during startup when symbol/source state is terminally invalid
  (`symbol`/`source` missing, inactive, or non-live source type), then stops processing that subscription
  immediately so it does not consume worker cycles with repeated reconnect attempts.
- Only missing/inactive/non-live source lookups are terminal; transient symbol/source lookup errors remain
  retryable and continue through normal stream startup retry handling.
- Transient startup lookups that fail after initial missing-row classification increment
  `liveSubscriptionStartupLoadFailures` and emit `live_subscription_symbol_source_load_retryable`.
- `MARKET_WORKER_LIVE_STREAM_GAP_RECOVERY` plus `MARKET_WORKER_LIVE_STREAM_GAP_REQUEST_LIMIT` controls
  missing-final-candle recovery request creation.
- `MARKET_WORKER_LIVE_STREAM_MESSAGE_STALE_SECONDS` controls stale heartbeat handling:
  subscriptions with `last_message_at` older than this threshold and no active lease are marked `stale`
  before each claim attempt. Stale rows are intentionally skipped from active workclaim. When a new valid
  websocket message arrives, `MARKET_WORKER_LIVE_STREAM_MESSAGE_STALE_SECONDS`-exceeded rows are restored
  to `active`, and `liveSubscriptionsRevived` increments in `/metrics.json`.

`MARKET_WORKER_PROVIDER_MAX_CONCURRENCY` limits in-flight fetches per provider key. `MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS`
adds optional provider-key pacing before each fetch. These controls are independent from database
write concurrency and are intended for public REST providers with rate limits.

`MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD` and `MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS` pause a
provider key after repeated fetch failures. A paused provider returns `provider_circuit_open`, which
is retryable through the job queue policy.

`MARKET_WORKER_JOB_TIMEOUT_SECONDS` bounds one claimed job or direct polling request. When it
expires, the worker records `job_timeout` with a short `MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS`
cleanup context so the queue can retry according to its existing policy.

`MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS` lets the direct `provider_polling_requests`
fallback reclaim stale Go-claimed rows left in `running` after an interrupted worker. Reclaimed
rows are marked in request metadata and counted in `/metrics.json`.

## Schema Compatibility

Python owns SQLAlchemy models and Alembic migrations. The Go worker only inspects the resulting
Postgres contract.

Startup readiness requires the `candles`, `symbols`, and `data_sources` tables plus the columns the
worker reads or writes for candle validation and storage. In `jobs` mode, readiness also requires a
compatible `job_queue_items` table when present and a compatible `provider_polling_requests` table
when present because fallback direct requests can be claimed when the queue is empty. In
`provider_polling_requests` mode, readiness requires a compatible direct request table.

Optional tables remain optional. If an optional table exists but does not expose the columns the Go
worker needs, the worker skips that integration and reports the missing columns in
`optionalColumnProblems` from inspect mode and `/readyz`. This applies to job queue events,
provider polling errors, provider health snapshots, ingestion performance runs, ingestion
conflicts, and runtime worker heartbeat tables.

## Job Bridge

Primary mode claims `job_queue_items` when present. It also falls back to pending
`provider_polling_requests` when the job queue table is missing or no eligible jobs are available.

Supported job payload:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "provider": "mock_polling",
  "providerSymbol": "BTCUSDT",
  "timeframe": "1m",
  "startTime": "2026-05-06T10:00:00Z",
  "endTime": "2026-05-06T11:00:00Z",
  "limit": 100
}
```

If a payload contains `providerPollingRequestId`, the worker loads the canonical request row from
`provider_polling_requests`.

Unsupported job types, malformed payloads, unsupported providers, unsupported timeframes, and
secret-looking metadata fail terminally. Transient provider or database errors remain retryable and
respect the existing job queue attempt limits plus `MARKET_WORKER_RETRY_BACKOFF_SECONDS`.

For `job_queue_items`, the worker renews `locked_until` while a job is running. If renewal fails
transiently, it is counted in metrics and retried on the next renewal tick. If the lock is no longer
owned by the worker, the renewal loop stops and the job result update remains guarded by the queue
row state.

## Candle Policy

The existing `candles` table remains the source of truth. The worker mirrors the Python policy:

- insert new candles;
- update existing partial candles;
- finalize existing partial candles with final values;
- skip partial candles after a final candle exists;
- skip duplicate matching final candles;
- reject and record conflicting final candles.

Decimal values remain strings until validation and are inserted into Postgres numeric columns.
The worker does not synthesize missing candles.

## Providers

- `mock_polling`: deterministic local candles with no network.
- `binance_public_rest`: Binance public `/api/v3/klines`, no API key.
- `generic_ohlc_http`: safe extension stub that returns explicit not-configured errors.

## Docker

```sh
docker build -f apps/go/market-worker/Dockerfile -t trading-go-market-worker .
docker run --rm \
  -e DATABASE_URL=postgresql://trading:trading@host.docker.internal:5432/trading_intelligence \
  -p 8091:8091 \
  trading-go-market-worker
```

## Verification

```sh
go test ./...
go vet ./...
go build ./cmd/market-worker
```
