# Reasoning Action Worker

The reasoning action worker processes due backend-safe follow-up work created by reasoning action
plans. It is an operations runtime for deterministic backend work, not a broker executor, alert
system, auto-trader, copy-trading feature, chatbot, or financial-advice layer.

## Command

```sh
cd apps/api
.venv/bin/python -m app.workers.reasoning_actions_worker
```

The worker requires `DATABASE_URL`. API startup does not start this worker and does not require the
worker to be enabled.

## Settings

```txt
REASONING_ACTION_WORKER_ENABLED=false
REASONING_ACTION_WORKER_POLL_SECONDS=10
REASONING_ACTION_WORKER_BATCH_SIZE=25
REASONING_ACTION_WORKER_MAX_CONCURRENCY=4
REASONING_ACTION_WORKER_LOCK_SECONDS=120
REASONING_ACTION_WORKER_MAX_ATTEMPTS=3
REASONING_ACTION_WORKER_JITTER_SECONDS=2
```

`REASONING_ACTION_WORKER_ENABLED=false` is safe for API processes. Set it to `true` only for the
worker process that should poll and execute due action items.

## Safe Action Types

The worker can execute:

- `evaluate_outcome_after_horizon`
- `run_replay`
- `run_news_correlation`
- `wait_for_more_final_candles`
- `no_action`

`request_human_review` stays pending for a manual workflow. The worker does not send notifications
or auto-complete review items.

The worker does not run profile diagnostics and does not apply calibration recommendations. Stored
outcomes produced by worker-executed evaluation actions can later be read by diagnostics through the
normal diagnostics API.

Rejected trading actions include `buy`, `sell`, `enter_trade`, `exit_trade`, `place_order`,
`risk_instruction`, `target_instruction`, `margin_instruction`, `position_instruction`,
`copy_trade`, and `execute_trade`. They are not selected by the worker and are never broker/order
instructions.

## Claiming And Locks

Due execution uses database leases:

- Eligible items have status `pending` or `due`, are due now, are below max attempts, and are one of
  the executable safe action types.
- Expired `running` items can be reclaimed after `locked_until`.
- Claimed items are marked `running`, assigned `locked_by`, assigned `locked_until`, increment
  `attempts`, and set `last_attempted_at`.
- Claiming uses row locking with `FOR UPDATE SKIP LOCKED` on PostgreSQL.
- Completed, skipped, cancelled, failed-max-attempt, human review, and rejected/trading actions are
  not claimed.

## Execution Behavior

- `evaluate_outcome_after_horizon` calls deterministic outcome evaluation after enough final future
  candles exist. If candles are still missing, the item returns to `pending` with a future due time.
- `run_replay` creates a deterministic replay run through the replay service. Replay-of-replay is
  skipped unless the item input explicitly allows it, and an existing linked replay is reused/skipped
  instead of creating loops.
- `run_news_correlation` runs deterministic news correlation against stored news events and persisted
  signal artifacts.
- `wait_for_more_final_candles` checks final candle availability and remains pending until enough
  final candles are available.
- `no_action` is marked skipped with a stable reason.

Failures store safe `error_code` and bounded `error_message` fields. Public `result_json` stores a
small failure summary, not stack traces. Retryable failures return to `pending` until attempts reach
the effective max attempt count.

## Worker Runs

Each poll creates a `reasoning_action_worker_runs` record with:

- `worker_id`
- optional `workspace_id`
- status
- batch limit
- claimed/completed/skipped/failed counts
- start and completion timestamps
- compact metadata

Structured logs include startup, shutdown, poll start/completion, item claimed, item started,
completed, skipped, failed, retry scheduled, and max-attempt events.

## Operational APIs

```txt
POST /action-items/mark-due
POST /action-items/execute-due
GET /action-items/worker/status
```

`POST /action-items/execute-due` uses the same claim-and-execute runner path as the worker. The API
does not require the worker process to be running for health or readiness.

## Deployment Notes

Run one or more worker processes separately from the API only after migrations are applied. The
database lease prevents duplicate processing across concurrent workers. A future external scheduler
can supervise this command, but no external scheduler dependency is required by the application.
