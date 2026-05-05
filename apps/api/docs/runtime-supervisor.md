# Runtime Supervisor

The runtime supervisor is a database-backed control plane for backend worker and operation status.
It records which runtime workers are installed, whether they are available or disabled, which
instances have checked in, which instances are stale, and which operator run requests were recorded.

It is not an OS process manager. It does not execute shell commands, start worker processes, place
orders, execute broker workflows, auto-trade, mutate signal classifications, or provide financial
advice.

## Tables

```txt
runtime_worker_definitions
runtime_worker_instances
runtime_worker_run_requests
```

Worker definitions are global metadata rows keyed by stable worker keys. Worker instances are
heartbeat rows keyed by `worker_id` and may optionally be scoped to a workspace. Run requests are
operator/system requests for safe backend worker actions and record status, inputs, results, and
errors.

## Settings

```txt
RUNTIME_SUPERVISOR_VERSION=v1
RUNTIME_WORKER_STALE_SECONDS=120
RUNTIME_WORKER_HEARTBEAT_ENABLED=true
RUNTIME_SUPERVISOR_RUN_REQUESTS_ENABLED=true
```

These settings are optional and do not require Redis or external infrastructure at API startup.
Workers still require `DATABASE_URL` because their normal runtime work already uses database state.

## Default Workers

`POST /runtime-supervisor/seed-default-workers` seeds or refreshes default definitions for:

- `live_feed_worker`
- `live_stale_monitor`
- `reasoning_actions_worker`
- `market_scan_worker`
- `provider_polling_operations`
- `notification_delivery_worker` when installed
- `data_retention_worker` when installed
- `metrics_snapshot_worker` when installed
- `backfill_worker` when installed

Definitions include descriptive command metadata such as `python -m app.workers.market_scan_worker`.
The API never executes those strings.

## Heartbeats

Long-running worker runtimes send optional heartbeats through the database-backed supervisor service:

```txt
starting -> running -> stopped
```

Heartbeat payloads are bounded operational metadata such as claimed counts, scan run counts, or
active subscription task counts. If worker definitions have not been seeded yet, heartbeat writes are
ignored so worker startup is not blocked.

`POST /runtime-supervisor/mark-stale` marks `starting`, `running`, and `unknown` instances stale
when their `last_heartbeat_at` is older than `RUNTIME_WORKER_STALE_SECONDS`.

## Run Requests

`POST /runtime-supervisor/run-requests` records operator run requests. Supported request types are:

```txt
run_once
execute_due
refresh_status
dry_run
```

`refresh_status` and `dry_run` complete as supervisor metadata operations. `execute_due` can call
existing safe integrations for:

- `reasoning_actions_worker`: executes due backend-safe reasoning action items.
- `market_scan_worker`: executes due deterministic scheduled scans over stored candles.

Other workers return `unsupported` until a safe explicit integration exists. Run requests never
start OS processes, execute arbitrary commands, call broker APIs, or bypass existing worker safety
rules. Provider polling remains behind the existing explicit provider polling and gap recovery APIs.

## API Contracts

```txt
POST /runtime-supervisor/seed-default-workers
GET /runtime-supervisor/workers
GET /runtime-supervisor/workers/{worker_key}
GET /runtime-supervisor/instances
POST /runtime-supervisor/instances/heartbeat
POST /runtime-supervisor/mark-stale
GET /runtime-supervisor/health
POST /runtime-supervisor/run-requests
GET /runtime-supervisor/run-requests/{request_id}
```

`GET /runtime-supervisor/health` returns supervisor version, heartbeat/run-request settings,
worker counts, running and stale instance counts, run request counters, and per-worker summaries.

## Deployment Notes

Run migrations before using the supervisor API:

```sh
cd apps/api
.venv/bin/alembic upgrade head
```

Seed definitions after deploy or during operational setup:

```sh
curl -X POST "$API_BASE_URL/runtime-supervisor/seed-default-workers"
```

Standalone workers and the multi-worker supervisor continue to run the same way. The runtime
supervisor adds status reporting and safe run request records around those runtimes without changing
their business behavior.
