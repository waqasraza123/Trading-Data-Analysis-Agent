# Go Market Data Worker

The Go market data worker is the first additive Go sidecar for this repository. It bridges to the
existing Python/Postgres platform without migrating or replacing the FastAPI backend.

Python remains the product brain:

- FastAPI routes and UI-facing contracts
- auth, RBAC, and workspace permissions
- SQLAlchemy models and Alembic migrations
- deterministic intelligence and reporting
- LLM reasoning and explanations
- product orchestration and readiness workflows

Go owns only selected sidecar execution:

- high-concurrency provider polling
- batch candle validation and normalization
- batch candle writes to the existing candle contract
- provider polling request counts/errors
- provider health snapshots when the table exists
- candle ingestion performance/conflict diagnostics when the tables exist
- runtime worker heartbeat when supervisor tables exist
- local health and metrics endpoints

It does not classify signals, calculate trading advice, place orders, connect to brokers for
execution, send alerts, mutate strategy profiles, run LLMs, expose public advice, or replace
FastAPI.

## Location

```txt
apps/go/market-worker
```

## Tables Used

Required:

- `candles`
- `symbols`
- `data_sources`
- either `job_queue_items` or `provider_polling_requests`

Optional integrations:

- `job_queue_events`
- `provider_polling_errors`
- `provider_health_snapshots`
- `candle_ingestion_performance_runs`
- `candle_ingestion_conflicts`
- `runtime_worker_definitions`
- `runtime_worker_instances`
- `engine_execution_records`

The worker detects table and column capabilities at startup. Optional tables are skipped when
missing. No Python migration is required for this phase.

## Job Queue Bridge

When `job_queue_items` exists, the worker claims eligible jobs with row locks and skip-locked
semantics. Eligibility includes configured queue name or provider polling job types, pending or
retryable status, available scheduling, attempts below max attempts, and expired or missing locks.

Supported job types:

- `provider_polling.fetch`
- `market_data.poll`
- `candles.fetch_provider`
- `provider_polling.run`

Current Python migrations constrain job types to the existing backend-safe set, so
`provider_polling.fetch` is the canonical current job type.

If `job_queue_items` is missing or no eligible jobs are present, the worker can claim pending
`provider_polling_requests` directly and update those rows through running, completed,
completed-with-warnings, or failed states.

Terminal failures are not retried by the Go bridge: unsupported job type, invalid payload,
unsupported provider, unsupported timeframe, secret-looking metadata, and not-configured provider
stubs. Transient provider or database failures remain retryable through the existing job queue
attempt limits and `MARKET_WORKER_RETRY_BACKOFF_SECONDS`.

The worker renews `job_queue_items.locked_until` while claimed jobs are running, so provider calls
or larger candle batches do not become eligible for another worker before completion. Lock renewal
is scoped to the same `locked_by` worker ID and running status.

## Candle Semantics

The worker writes to the existing `candles` table and mirrors the Python source-of-truth policy:

- final candles are the default;
- partial candles do not overwrite existing final candles;
- duplicate final candles with identical values are skipped;
- conflicting final candles are kept out of storage and recorded as conflicts/errors;
- partial candles may be updated or finalized;
- timestamps must align with timeframe;
- invalid OHLC rows are rejected;
- decimal price and volume values are handled as strings before numeric insertion;
- missing candles are not synthesized.

## Providers

- `mock_polling`: deterministic no-network provider for local development and tests.
- `binance_public_rest`: Binance public REST `/api/v3/klines`, no API key.
- `generic_ohlc_http`: safe extension stub that returns explicit not-configured errors.

## Run

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
go run ./cmd/market-worker
```

Run modes:

- `MARKET_WORKER_RUN_MODE=serve`: default long-running worker with health endpoints.
- `MARKET_WORKER_RUN_MODE=once`: claim and process one bounded batch, then exit.
- `MARKET_WORKER_RUN_MODE=inspect`: print detected database capabilities as JSON and exit without claiming work.

Concurrency knobs:

- `MARKET_WORKER_BATCH_SIZE`: number of jobs or direct requests claimed per cycle.
- `MARKET_WORKER_MAX_CONCURRENCY`: number of claimed jobs or direct requests processed in parallel.
- `MARKET_WORKER_PROVIDER_MAX_CONCURRENCY`: in-flight fetch limit per provider key.
- `MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS`: optional pacing interval between fetch starts per provider key.
- `MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD`: consecutive fetch failures before a provider key is paused.
- `MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS`: provider pause duration after the failure threshold is reached.
- `MARKET_WORKER_JOB_TIMEOUT_SECONDS`: max runtime for one claimed job or direct request.
- `MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS`: bounded cleanup timeout for job/request status writes.
- `MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS`: stale age before a Go-claimed direct request can be reclaimed.

Docker:

```sh
docker compose --profile workers up --build go-market-worker
```

## Health

```txt
GET /healthz
GET /readyz
GET /metrics.json
```

`/readyz` exposes DB connectivity, provider registry state, and detected database capabilities.
`/metrics.json` exposes job, timeout, reclaimed direct request, candle, provider failure, provider
gate wait, provider circuit breaker, job lock renewal, and capability counters as JSON.

## Operational Checks

Use inspect mode before enabling a new environment:

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence \
MARKET_WORKER_RUN_MODE=inspect \
go run ./cmd/market-worker
```

Readiness requires a database connection, `candles`, `symbols`, `data_sources`, at least one work
source from `job_queue_items` or `provider_polling_requests`, and at least one enabled provider.
Missing optional provider health, ingestion diagnostics, runtime heartbeat, and job event tables
are reported as capabilities but do not block the worker.

## Enqueue From Python/API

Use the existing job queue API with `provider_polling.fetch` and a provider polling payload:

```json
{
  "queueName": "market-data",
  "jobType": "provider_polling.fetch",
  "payloadJson": {
    "workspaceId": "00000000-0000-0000-0000-000000000000",
    "sourceId": "00000000-0000-0000-0000-000000000000",
    "symbolId": "00000000-0000-0000-0000-000000000000",
    "provider": "mock_polling",
    "providerSymbol": "BTCUSDT",
    "timeframe": "1m",
    "limit": 100
  }
}
```

The existing Python provider polling API remains available and unchanged.

## Future Extensions

- Provider-specific OHLC HTTP mappings.
- COPY-optimized candle write path after DB contract review.
- More detailed provider health reconciliation.
- Deeper engine execution record linkage for market data jobs.
