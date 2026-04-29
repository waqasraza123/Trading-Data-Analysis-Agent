# Backend Operations

This backend is a deterministic trading intelligence API. It does not include UI, broker
execution, auto-trading, LLM calls, news correlation, alerts, billing, or copy/social trading.

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
SEED_DEFAULT_WORKSPACE_NAME=
SEED_DEFAULT_ADMIN_EMAIL=
SEED_DEFAULT_ADMIN_NAME=
```

Optional secrets are not required at API startup. `ADMIN_API_KEY` is required only when
`AUTH_ENABLED=true`. `LIVE_FEED_API_KEY` is required only for providers that require a key.

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
```

Workers require `DATABASE_URL`. They emit structured lifecycle logs and stop gracefully on
`SIGINT` or `SIGTERM`.

## Health Endpoints

```txt
GET /health
GET /health/live
GET /health/db
GET /health/ready
GET /health/workers
```

`/health` and `/health/live` report API process liveness. `/health/db` checks database
connectivity. `/health/ready` is suitable for readiness probes because it requires database
connectivity. `/health/workers` reports live worker and stale monitor status when the database is
available and returns a degraded safe status otherwise.

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
replay_requested
replay_failed
analysis_failed
```

Request logs include `request_id`, method, path, status code, duration in milliseconds, safe client
host, and error code when available. Bodies, uploads, tokens, API keys, database URLs, and live feed
keys are not logged.
