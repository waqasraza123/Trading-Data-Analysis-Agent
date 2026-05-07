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

## Configuration

Required:

- `DATABASE_URL`

Optional:

- `MARKET_WORKER_ID`
- `MARKET_WORKER_QUEUE_NAME`, default `market-data`
- `MARKET_WORKER_POLL_SECONDS`, default `5`
- `MARKET_WORKER_BATCH_SIZE`, default `10`
- `MARKET_WORKER_JOB_LOCK_SECONDS`, default `120`
- `MARKET_WORKER_PROVIDER_TIMEOUT_SECONDS`, default `20`
- `MARKET_WORKER_MAX_CANDLES_PER_REQUEST`, default `1000`
- `MARKET_WORKER_HEALTH_ADDR`, default `:8091`
- `MARKET_WORKER_LOG_LEVEL`, default `info`
- `MARKET_WORKER_MODE`, default `jobs`
- `MARKET_WORKER_RUN_MODE`, default `serve`
- `MARKET_WORKER_RETRY_BACKOFF_SECONDS`, default `60`
- `BINANCE_PUBLIC_REST_BASE_URL`, default `https://api.binance.com`
- `MARKET_WORKER_ENABLE_BINANCE_PUBLIC`, default `true`
- `MARKET_WORKER_ENABLE_MOCK_PROVIDER`, default `true`

The worker does not require Redis, LLM keys, OCR keys, broker credentials, or external provider
credentials at startup.

## Run Modes

- `serve`: long-running worker with health endpoints, DB heartbeat when available, and periodic job claiming.
- `once`: claim and process one bounded batch, then exit.
- `inspect`: connect to Postgres, detect table capabilities, print JSON, and exit without claiming work.

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
