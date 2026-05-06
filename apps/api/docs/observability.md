# Production Observability

Production observability exposes internal service metrics, SLO status, persisted SLO snapshots, and
optional tracing status for backend operations.

This layer is operational monitoring only. It does not call brokers, execute trades, send user
alerts, start workers, call external observability providers, or provide financial advice.

## Settings

Defaults:

```txt
OBSERVABILITY_ENABLED=true
METRICS_ENDPOINT_ENABLED=true
TRACING_ENABLED=false
SLO_VERSION=v1
REQUEST_LATENCY_WARNING_MS=1000
WORKER_STALE_WARNING_SECONDS=300
PROVIDER_FAILURE_WARNING_COUNT=3
STALE_DATA_WARNING_COUNT=5
```

No external observability provider is required at API startup. `DATABASE_URL` is optional for
startup and liveness. Database-backed metrics and SLO components report `unknown` when the database
is unavailable or optional tables have not been migrated.

## Metrics Endpoints

```txt
GET /observability/metrics
GET /observability/metrics.json
```

`/observability/metrics.json` always returns JSON when observability and metrics endpoints are
enabled. It includes in-process HTTP counters and duration summaries, plus database-backed
operation counters when a database is configured.

`/observability/metrics` returns a Prometheus-compatible text format without requiring a
Prometheus dependency. If a Prometheus client is added later, this endpoint can be upgraded without
changing callers.

Tracked metrics include:

- HTTP request count by method, normalized path, and status.
- HTTP request duration summaries and buckets.
- Analysis runs by status.
- Provider polling requests by status and provider.
- Provider health snapshots by status and freshness.
- Live subscription status counts.
- Stale market memory counts.
- Data quality findings by severity.
- Runtime worker instance and run-request statuses.
- Notification message/event statuses when present.
- Job queue depth and status counts when `job_queue_items` exists.
- Failed backend operation counts.

Request bodies, uploads, tokens, API keys, database URLs, provider credentials, and raw secrets are
not captured.

## SLO Endpoints

```txt
GET /observability/slo
POST /observability/slo/snapshot
```

`GET /observability/slo` computes the current service SLO from:

- `api_readiness`
- `db_health`
- `worker_health`
- `provider_health`
- `data_freshness`
- `queue_health`
- `error_rate`
- `latency_status`

Component and aggregate labels are:

```txt
healthy
degraded
failing
unknown
```

Unknown optional components do not fail the aggregate when other known components are healthy.
Failing components take priority over degraded components.

`POST /observability/slo/snapshot` persists the current SLO payload to
`service_slo_snapshots`. It requires `DATABASE_URL` and existing migrations.

## SLO Snapshot Table

```txt
service_slo_snapshots
```

Fields:

```txt
id
workspace_id nullable
status
slo_version
snapshot_json
created_at
```

Indexes:

```txt
ix_service_slo_snapshots_workspace_created
ix_service_slo_snapshots_status
```

## Tracing

```txt
GET /observability/tracing/status
```

Tracing is disabled by default with `TRACING_ENABLED=false`. When enabled, the API reports local
tracing hooks for request id, request duration, request status, and optional trace context. The
current implementation does not export to an external collector and does not require any tracing
provider at startup.

## Deployment Notes

Run migrations before using SLO snapshots:

```sh
cd apps/api
.venv/bin/alembic upgrade head
```

Metrics endpoints can be scraped by internal infrastructure. Keep them internal to the deployment
network or protected at the gateway if production exposure is not desired.

This observability layer is intentionally separate from product notifications. It must not become
user-facing alerts, trading alerts, broker execution, auto-trading, or advice output.
