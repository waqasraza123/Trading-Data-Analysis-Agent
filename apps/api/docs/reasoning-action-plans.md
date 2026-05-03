# Backend-Safe Reasoning Action Plans

Reasoning action plans convert persisted scenario reasoning into bounded backend follow-up work.
They do not execute trades, send alerts, provide financial advice, or schedule external
notifications.

## Purpose

Scenario reasoning may suggest backend-safe actions such as evaluating outcomes later, running a
deterministic replay, correlating stored news context, waiting for more final candles, or requesting
human review. The action planner validates those suggestions, persists an auditable plan, and creates
idempotent action items that can be tracked or manually executed.

The deterministic artifacts remain the source of truth. Action plans only orchestrate follow-up
backend work over those artifacts.

## Persistence

Action plans are stored in `reasoning_action_plans`. Individual follow-up items are stored in
`reasoning_action_items`.

Plans track source type, source id, linked signal/analysis/reasoning run, status, plan version,
created-from source, summary, and metadata for skipped or rejected suggestions.

Items track source links, action type, status, priority, due time, horizon, idempotency key, bounded
input JSON, result JSON, attempts, errors, lease owner, lease expiry, and completion timestamps. The
database enforces one item per workspace/idempotency key.

## Allowed Actions

Allowed backend actions are:

- `evaluate_outcome_after_horizon`
- `run_replay`
- `run_news_correlation`
- `wait_for_more_final_candles`
- `request_human_review`
- `no_action`

Explicitly rejected actions include:

- `buy`
- `sell`
- `enter_trade`
- `exit_trade`
- `place_order`
- `set_stop_loss`
- `target_instruction`
- `use_leverage`
- `open_position`
- `close_position`
- `copy_trade`
- `execute_trade`

Rejected actions are never persisted as executable work. They are recorded in plan metadata, and the
planner can create a safe `request_human_review` item when a rejected action appears.

## Planning Behavior

`ReasoningActionPlanner` loads a reasoning run, its scenario hypotheses, the linked signal, and the
linked analysis run. It extracts `suggestedBackendActions`, validates them, builds stable
idempotency keys, and creates bounded items.

Planning rules:

- `evaluate_outcome_after_horizon` creates missing outcome items for configured horizons, defaulting
  to `5,15,30,60`. Existing outcomes for the current evaluation version are skipped.
- Outcome item `due_at` is the analysis reference time plus the horizon. If enough final future
  candles already exist, the item starts as `due`.
- `run_replay` creates a manual replay item using `latest_engine_version` and avoids replay-of-replay
  loops.
- `run_news_correlation` creates an item only when the signal has no existing stored correlations.
- `wait_for_more_final_candles` creates an item due after the expected final-candle availability
  window.
- `request_human_review` creates a pending item and does not send a notification.
- `no_action` completes the plan without executable work.

## Execution Behavior

`ReasoningActionExecutor` supports explicit item execution. Scheduled and API due execution use
`ReasoningActionRunner`, which claims items with database leases before calling the executor. Items
transition through `pending` or `due` to `running`, then `completed`, `skipped`, `failed`, or back
to `pending` when final candles are not available yet.

Execution dispatch:

- `evaluate_outcome_after_horizon` calls the deterministic outcome evaluation service for due
  horizons only after enough final candles exist.
- `run_replay` calls the deterministic replay service, skips replay-of-replay by default, and avoids
  creating duplicate linked replay runs.
- `run_news_correlation` calls the deterministic news correlation service.
- `wait_for_more_final_candles` checks candle availability and completes only when enough final
  candles exist.
- `request_human_review` remains pending for a human process.
- `no_action` is skipped with a stable reason.

Due execution includes deterministic replay items because they are backend-safe and idempotent at the
action item level. Human review requires a person or future review workflow and is not claimed by the
worker.

## APIs

```txt
POST /reasoning/runs/{reasoning_run_id}/action-plan
GET /reasoning/runs/{reasoning_run_id}/action-plan
GET /action-plans/{action_plan_id}
GET /action-plans/{action_plan_id}/items
POST /action-items/{action_item_id}/execute
POST /action-items/mark-due
POST /action-items/execute-due
GET /action-items/due
GET /action-items/worker/status
```

Create request:

```json
{
  "forceRecompute": false
}
```

Execute due request:

```json
{
  "workspaceId": null,
  "limit": 100
}
```

## Audit Events

When a linked analysis run is available, the planner and executor write audit events for requested
plans, created plans, created items, rejected items, due items, started execution, completed
execution, skipped execution, and failed execution.

## Scheduled Worker

Run due action processing with:

```sh
python -m app.workers.reasoning_actions_worker
```

The worker polls for due executable items, claims them with `locked_by` and `locked_until`, executes
bounded batches, records `reasoning_action_worker_runs`, and logs structured lifecycle events. It
does not send alerts, notifications, broker orders, or financial advice. See
`docs/reasoning-action-worker.md` for operational details.
