# Go Market Worker Operations

This runbook covers the additive market data sidecar under `apps/go/market-worker`. Python remains
the canonical API, auth, migrations, product orchestration, deterministic intelligence, LLM, and
UI-contract layer.

## Preflight

Run compatibility inspection before enabling a new environment:

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=inspect \
go run ./cmd/market-worker
```

The JSON output includes worker identity, queue, run mode, registered providers, detected database
capabilities, required column problems, optional column problems, and readiness status. Required
capabilities are compatible `candles`, `symbols`, `data_sources`, and at least one compatible work
source from `job_queue_items` or `provider_polling_requests`.

Optional provider health, ingestion performance, conflict, runtime heartbeat, and job event tables
are reported but do not block startup. If one of those optional tables exists with missing columns,
the worker skips that integration and reports it in `optionalColumnProblems`.

## Schema Contract Checks

The Go worker does not own migrations. It validates the Postgres shape produced by the Python
Alembic migrations before it claims work.

Readiness blocks when required tables or required columns are missing. Core required contracts are:

- `candles` for source-of-truth candle reads and writes;
- `symbols` and `data_sources` for active symbol/source validation;
- `job_queue_items` when the table exists in jobs mode;
- `provider_polling_requests` when direct request mode is selected or the table exists as a
  fallback work source.

Optional integrations are enabled only when both the table and the columns used by the worker are
present. Optional compatibility problems do not block candle ingestion, but they explain why the
worker is not writing job events, provider polling errors, provider health snapshots, ingestion
performance rows, ingestion conflicts, or runtime heartbeats.

## Execution Modes

Long-running service:

```sh
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=serve \
go run ./cmd/market-worker
```

Single bounded batch:

```sh
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=once \
go run ./cmd/market-worker
```

Compatibility inspection:

```sh
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=inspect \
go run ./cmd/market-worker
```

## Live Runtime Processing

Live runtime processing is only active in `jobs` mode when:

- `MARKET_WORKER_ENABLE_LIVE_STREAM=true`;
- `MARKET_WORKER_ENABLE_LIVE_BINANCE=true`;
- `live_feed_subscriptions` and `live_feed_events` are schema-compatible.

Operational defaults:

- `MARKET_WORKER_LIVE_STREAM_CLAIM_INTERVAL_SECONDS` (claim loop cadence, default `5s`)
- `MARKET_WORKER_LIVE_STREAM_CLAIM_BATCH_SIZE` (max subscriptions per cycle, default batch-size)
- `MARKET_WORKER_LIVE_STREAM_LEASE_SECONDS` (lease ownership TTL, default `90s`)
- `MARKET_WORKER_LIVE_STREAM_RECONNECT_SECONDS` (reconnect backoff, default `5s`)
- `MARKET_WORKER_LIVE_STREAM_READ_TIMEOUT_SECONDS` (websocket read deadline, default `30s`)

Operational checks in serve mode:

- `/readyz` must remain green with `ready: true` after startup
- `/metrics.json` should show live counters increasing for active streams:
  - `liveSubscriptionsClaimed`
  - `liveSubscriptionsStarted`
  - `liveReconnects`
  - `liveMessagesReceived`
  - `liveCandlesWritten`
  - `liveGapRequests`
- Worker logs should show:
  - `market_worker_live_claim_failed`
  - `market_worker_live_lease_lost`
  - `market_worker_live_lease_release_failed`
  - `market_worker_live_subscription_stream_reconnect`

## Concurrency And Locks

`MARKET_WORKER_BATCH_SIZE` controls claim size. `MARKET_WORKER_MAX_CONCURRENCY` controls how many
claimed items run at the same time. The default concurrency equals batch size.

For `job_queue_items`, claimed rows are protected by `locked_by` and `locked_until`. While a job is
running, the worker renews `locked_until` on a bounded interval derived from
`MARKET_WORKER_JOB_LOCK_SECONDS`. Renewal only succeeds when the row is still running and still
locked by the current worker ID.

Use lower concurrency for public providers with strict rate limits or when the database pool is
small. Raise batch size independently when claim overhead matters but execution should remain
bounded.

## Execution Timeouts

`MARKET_WORKER_JOB_TIMEOUT_SECONDS` bounds one claimed `job_queue_items` row or direct
`provider_polling_requests` row. A timed-out item is recorded as `job_timeout`, counted in
`jobsTimedOut`, and treated as retryable by the existing job queue policy.

`MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS` is the cleanup timeout for completion, failure, and direct
request status writes. If the processing context has already expired, the worker uses a fresh
bounded cleanup context so status updates can still be recorded without hanging shutdown forever.

## Direct Request Recovery

`provider_polling_requests` does not have native lock columns. The Go fallback claim path marks
rows with Go claim metadata and can reclaim interrupted Go-owned `running` rows once
`MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS` has elapsed. Reclaimed rows are counted as
`providerRequestsReclaimed` in `/metrics.json`.

The stale window should be at least as long as `MARKET_WORKER_JOB_TIMEOUT_SECONDS` in most
deployments. Set it to `0` to disable stale direct request reclaiming.

## Provider Backpressure

`MARKET_WORKER_PROVIDER_MAX_CONCURRENCY` limits concurrent fetches per provider key, independent of
job processing concurrency. `MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS` adds a minimum interval between
fetch starts for the same provider key. Use these settings to protect public REST providers and to
keep provider latency from overwhelming candle writes.

Provider gate wait time is reported in `/metrics.json` as `providerGateWaits` and
`providerGateWaitMillis`. Sustained growth means the worker is intentionally pacing provider calls;
raise provider limits only after checking provider rate limits, database write capacity, and candle
conflict counts.

## Provider Circuit Breaker

`MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD` opens a per-provider circuit after consecutive fetch
failures. `MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS` controls how long the provider key stays
paused. Set the threshold to `0` to disable circuit breaking.

When a circuit is open, work fails with `provider_circuit_open`. That error is retryable through
the existing job queue policy, and provider health is recorded as failing when the optional provider
health table exists. `/metrics.json` reports `providerCircuitOpenings` and
`providerCircuitBlocks`.

## Failure Policy

Terminal failures are completed as failed or dead-lettered without scheduling Go-side retry:

- unsupported job type;
- invalid job payload;
- unsupported provider;
- unsupported timeframe;
- secret-looking metadata;
- not-configured provider stub.

Retryable failures use the existing job queue attempt policy and
`MARKET_WORKER_RETRY_BACKOFF_SECONDS`:

- provider network or timeout failures;
- job timeout failures;
- public provider HTTP failures;
- provider circuit-open responses;
- transient database contention;
- serialization or deadlock errors;
- unknown operational errors.

For direct `provider_polling_requests` fallback work, failures are recorded on the request row when
the table and columns are available.

## Health Endpoints

When `MARKET_WORKER_RUN_MODE=serve`, the worker exposes:

```txt
GET /healthz
GET /readyz
GET /metrics.json
```

`/healthz` reports process liveness, worker ID, and uptime. `/readyz` checks database connectivity,
required table and column capabilities, optional column problems, and provider registration.
`/metrics.json` reports job, candle, timeout, reclaimed direct request, provider failure, provider
gate wait, provider circuit breaker, job lock renewal, and capability counters.

## Rollout Sequence

1. Run `MARKET_WORKER_RUN_MODE=inspect` against the target database.
2. Confirm required capabilities and provider registration.
3. Run `MARKET_WORKER_RUN_MODE=once` with the mock provider and a small queued job.
4. Review `candles`, `provider_polling_requests`, optional job events, optional conflicts, and
   optional provider health snapshots.
5. Enable `MARKET_WORKER_RUN_MODE=serve` behind the worker process manager.
6. Watch `/readyz`, `/metrics.json`, runtime heartbeat rows when available, and job queue
   dead-letter counts.
7. Tune `MARKET_WORKER_BATCH_SIZE`, `MARKET_WORKER_MAX_CONCURRENCY`, and
   `MARKET_WORKER_JOB_LOCK_SECONDS` from observed provider latency, conflict counts, and lock
   renewal failures.
8. Tune `MARKET_WORKER_PROVIDER_MAX_CONCURRENCY` and `MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS` from
   provider response codes, provider gate wait metrics, and provider-specific public REST limits.
9. Tune `MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD` and `MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS`
   from repeated provider failures, provider health snapshots, and job retry pressure.
10. Tune `MARKET_WORKER_JOB_TIMEOUT_SECONDS` and `MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS` from
    observed provider latency, candle batch size, and shutdown expectations.
11. Tune `MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS` from direct fallback usage and the maximum
    expected runtime of a provider polling request.

## Safety Boundary

The worker handles market data ingestion only. It must not classify signals, calculate trading
advice, place orders, connect to brokers for execution, send external alerts, mutate strategy
profiles, run LLMs, or replace FastAPI.
