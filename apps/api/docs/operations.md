# Backend Operations

This backend is a deterministic trading intelligence API. It does not include UI, broker
execution, auto-trading, alerts, billing, or copy/social trading. Optional LLM explanations can
be enabled, but they only explain persisted deterministic artifacts and do not classify signals.

## Required Runtime Variables

```txt
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=postgresql://user:password@host.neon.tech/database?sslmode=require
```

`DATABASE_URL` is optional for API startup so local liveness checks can run without secrets. It is
required for migrations, seed, database-backed routes, readiness, live workers, and stale monitor
processes.

## Optional Runtime Variables

```txt
API_PREFIX=
REDIS_URL=
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=false
AUTH_ENABLED=false
ADMIN_API_KEY=
API_KEY_HEADER_NAME=x-admin-api-key
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60
MAX_REQUEST_BODY_BYTES=1048576
MAX_UPLOAD_FILE_BYTES=10485760
LIVE_FEED_PROVIDER=
LIVE_FEED_API_KEY=
LIVE_FEED_RECONNECT_INITIAL_SECONDS=1
LIVE_FEED_RECONNECT_MAX_SECONDS=60
LIVE_FEED_RECONNECT_MULTIPLIER=2
LIVE_FEED_STALE_MESSAGE_SECONDS=180
LIVE_FEED_STALE_FINAL_CANDLE_SECONDS=300
LIVE_FEED_WORKER_POLL_SECONDS=10
NEWS_CORRELATION_PRE_EVENT_MINUTES=5
NEWS_CORRELATION_POST_EVENT_MINUTES=30
NEWS_CORRELATION_MAX_EVENTS_PER_SIGNAL=10
LLM_EXPLANATIONS_ENABLED=false
LLM_PROVIDER=mock
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=12
LLM_MAX_INPUT_TOKENS=1800
LLM_MAX_OUTPUT_TOKENS=450
OPENAI_API_KEY=
LLM_STORE_INPUTS=false
LLM_STORE_OUTPUTS=true
NOTIFICATION_WORKER_ENABLED=false
NOTIFICATION_WORKER_POLL_SECONDS=10
NOTIFICATION_WORKER_BATCH_SIZE=100
NOTIFICATION_WORKER_LOCK_SECONDS=120
NOTIFICATION_WORKER_MAX_ATTEMPTS=3
NOTIFICATION_WORKER_JITTER_SECONDS=2
MARKET_SCAN_WORKER_ENABLED=false
MARKET_SCAN_WORKER_POLL_SECONDS=30
MARKET_SCAN_WORKER_BATCH_SIZE=10
MARKET_SCAN_DEFAULT_LOOKBACK_MINUTES=60
MARKET_SCAN_DEFAULT_INTERVAL_SECONDS=60
WORKER_SUPERVISOR_COMPONENTS=
WORKER_SUPERVISOR_SHUTDOWN_TIMEOUT_SECONDS=20
SEED_DEFAULT_WORKSPACE_NAME=
SEED_DEFAULT_ADMIN_EMAIL=
SEED_DEFAULT_ADMIN_NAME=
```

Optional secrets are not required at API startup. `ADMIN_API_KEY` is required only when
`AUTH_ENABLED=true`. `LIVE_FEED_API_KEY` is required only for providers that require a key.
`OPENAI_API_KEY` is required only when LLM explanations are enabled with `LLM_PROVIDER=openai`.
`REDIS_URL` is required when rate limiting is enabled in staging or production.

## Running The API

```sh
cd apps/api
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

## Running Seed

```sh
cd apps/api
SEED_DEFAULT_WORKSPACE_NAME="Default Workspace" \
SEED_DEFAULT_ADMIN_EMAIL="admin@example.test" \
SEED_DEFAULT_ADMIN_NAME="Default Admin" \
.venv/bin/python -m app.cli seed
```

Seed logs `seed_started` and `seed_completed` without logging credentials.

## Running Workers

```sh
cd apps/api
python -m app.workers.live_feed_worker
python -m app.workers.live_stale_monitor
REASONING_ACTION_WORKER_ENABLED=true python -m app.workers.reasoning_actions_worker
NOTIFICATION_WORKER_ENABLED=true python -m app.workers.notification_worker
MARKET_SCAN_WORKER_ENABLED=true python -m app.workers.market_scan_worker
WORKER_SUPERVISOR_COMPONENTS=live_feed,stale_monitor,reasoning_actions,notifications,market_scans \
REASONING_ACTION_WORKER_ENABLED=true \
NOTIFICATION_WORKER_ENABLED=true \
MARKET_SCAN_WORKER_ENABLED=true \
python -m app.workers.supervisor
```

Workers require `DATABASE_URL`. They emit structured lifecycle logs and stop gracefully on
`SIGINT` or `SIGTERM`.

The supervisor entrypoint is optional and coordinates multiple worker runtimes in one process.
Details are documented in `docs/worker-supervisor.md`.

## Health Endpoints

```txt
GET /health
GET /health/live
GET /health/db
GET /health/ready
GET /health/redis
GET /health/workers
```

`/health` and `/health/live` report API process liveness. `/health/db` checks database
connectivity. `/health/ready` is suitable for readiness probes because it requires database
connectivity. `/health/redis` checks Redis connectivity when configured. `/health/workers` reports
live worker, stale monitor, and Redis status when the database is available and returns a degraded
safe status otherwise.

The API does not require the live worker to be running for readiness.

## Logs

Application logs are JSON and include stable event names such as:

```txt
app_startup
app_shutdown
request_completed
request_failed
db_health_failed
seed_started
seed_completed
worker_started
worker_stopped
live_worker_started
live_worker_stopped
stale_monitor_started
stale_monitor_stopped
scheduled_scan_due_found
scheduled_scan_run_started
scheduled_scan_run_completed
scheduled_scan_run_failed
replay_requested
replay_failed
analysis_failed
```

Request logs include `request_id`, method, path, status code, duration in milliseconds, safe client
host, and error code when available. Bodies, uploads, tokens, API keys, database URLs, and live feed
keys are not logged.
