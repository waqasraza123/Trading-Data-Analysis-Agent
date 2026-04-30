# Worker Supervisor

The worker supervisor is an optional production entrypoint for running multiple backend worker
runtimes in one managed process. Standalone worker entrypoints remain available for deployments that
prefer one process per worker.

## Run

```sh
WORKER_SUPERVISOR_COMPONENTS=live_feed,stale_monitor,reasoning_actions,notifications \
REASONING_ACTION_WORKER_ENABLED=true \
NOTIFICATION_WORKER_ENABLED=true \
.venv/bin/python -m app.workers.supervisor
```

The supervisor requires `DATABASE_URL`.

## Components

`WORKER_SUPERVISOR_COMPONENTS` accepts a comma-separated list:

```txt
live_feed
stale_monitor
reasoning_actions
notifications
```

`reasoning_actions` starts only when `REASONING_ACTION_WORKER_ENABLED=true`.
`notifications` starts only when `NOTIFICATION_WORKER_ENABLED=true`.

## Failure Behavior

The supervisor starts each selected runtime as an asyncio task. If a supervised worker fails or
stops unexpectedly, the supervisor stops every worker and exits with an error so the platform can
restart the process. `SIGINT` and `SIGTERM` trigger graceful shutdown.

Shutdown uses:

```txt
WORKER_SUPERVISOR_SHUTDOWN_TIMEOUT_SECONDS=20
```

If workers do not finish within the timeout, remaining tasks are cancelled.

## Boundaries

The supervisor does not change worker business behavior, database leases, safety rules, or
deterministic analysis contracts. It only coordinates runtime lifecycle.
