# Distributed Job Queue

The job queue module adds a backend workload orchestration layer for bounded internal work. It is
for imports, provider polling, scans, daily workflows, outcomes, reasoning, notifications,
read-model rebuilds, backfills, data-quality runs, retention apply jobs, LLM explanations, and
report builds.

It does not add broker execution, order placement, auto-trading, copy trading, trading alerts, shell
execution, arbitrary code execution, or financial-advice behavior.

## Storage

The default backend is database-backed and uses:

- `job_queue_definitions`
- `job_queue_items`
- `job_queue_events`

`JOB_QUEUE_BACKEND=database` is the default and requires only the existing database connection.
`JOB_QUEUE_BACKEND=redis` selects the Redis adapter path, but this phase keeps durable state in the
database-backed implementation so Redis is not required locally. `JOB_QUEUE_REDIS_URL` is optional.

## Settings

- `JOB_QUEUE_BACKEND=database`
- `JOB_QUEUE_DEFAULT_MAX_ATTEMPTS=3`
- `JOB_QUEUE_LOCK_SECONDS=300`
- `JOB_QUEUE_CLAIM_BATCH_SIZE=25`
- `JOB_QUEUE_RETRY_BACKOFF_SECONDS=60`
- `JOB_QUEUE_REDIS_URL`

## Job Types

Supported job types are:

- `import.csv`
- `import.json`
- `provider_polling.fetch`
- `scan.run`
- `daily_workflow.run`
- `outcome.evaluate`
- `reasoning.generate`
- `notification.deliver`
- `read_model.rebuild`
- `backfill.item`
- `data_quality.run`
- `retention.apply`
- `llm.explain`
- `report.build`

Seed default definitions with:

```bash
.venv/bin/python -m alembic upgrade head
curl -X POST http://localhost:8000/job-queue/definitions/seed-default
```

## Behavior

Jobs support idempotent enqueue with optional `workspaceId` plus `idempotencyKey`, priority,
`scheduledAt`, `availableAt`, claim locks, heartbeats, attempts, retry backoff, cancellation,
dead-letter state, and lifecycle events.

Payloads are JSON objects and must use one of the supported backend-safe job types. Payloads with
explicit unsafe operation types such as broker/order/trade execution are rejected.

## Worker

Run one queue worker with:

```bash
.venv/bin/python -m app.workers.job_queue_worker --queue scans
```

The worker also accepts `JOB_QUEUE_WORKER_QUEUE` and `JOB_QUEUE_WORKER_CONCURRENCY`.

The worker claims DB-backed jobs, dispatches only registered handlers, heartbeats through the runtime
supervisor, and fails unsupported job types with `unsupported_job_type`. It does not run shell
commands and does not execute arbitrary payload code.

## API

- `POST /job-queue/jobs`
- `GET /job-queue/jobs`
- `GET /job-queue/jobs/{job_id}`
- `POST /job-queue/jobs/{job_id}/cancel`
- `GET /job-queue/jobs/{job_id}/events`
- `POST /job-queue/definitions/seed-default`
- `GET /job-queue/definitions`

## Integration

Existing workers are not rewritten. Future modules can enqueue durable work through
`JobQueueService.enqueue_job(...)` and can register safe Python handlers with `JobQueueDispatcher`.
Handlers are explicit code registrations only; payloads never select import paths, shell commands,
or arbitrary callables.

When a job is connected to `engine_execution_records`, store `engineExecutionRecordId` in
`payloadJson`; the service preserves the link in job payload metadata.
