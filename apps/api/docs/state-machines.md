# Intelligence State Machine Registry

The state machine registry is a backend-only catalog of lifecycle rules for persisted intelligence objects. It centralizes allowed states, valid transitions, terminal states, lifecycle metadata, and optional validation audit records.

It does not execute broker actions, place orders, auto-trade, send trading advice, or rewrite existing services to enforce the registry immediately.

## Purpose

The registry answers four operational questions:

- Which statuses are allowed for each backend intelligence object type?
- Which status transitions are valid?
- Which states are terminal?
- Can a service or operator validate a transition before a status update?

The first phase is intentionally additive. Existing models, database check constraints, services, and routes keep their current status strings and behavior. Future services can adopt the shared validation helper before mutating status.

## Database Tables

`state_machine_definitions` stores versioned lifecycle definitions.

Fields:

- `id`
- `key`
- `version`
- `object_type`
- `states_json`
- `transitions_json`
- `terminal_states_json`
- `metadata_json`
- `status`
- `created_at`
- `updated_at`

Allowed definition statuses:

- `active`
- `draft`
- `archived`

`state_transition_validations` stores optional validation audit records.

Fields:

- `id`
- `workspace_id`
- `state_machine_key`
- `state_machine_version`
- `object_type`
- `object_id`
- `from_state`
- `to_state`
- `validation_status`
- `reason`
- `created_at`

Allowed validation statuses:

- `valid`
- `invalid`

## Default State Machines

The default seed includes:

- `import_batch`
- `live_feed_subscription`
- `analysis_run`
- `signal_classification`
- `outcome_evaluation`
- `reasoning_run`
- `reasoning_action_item`
- `operator_review_item`
- `dataset_export`
- `webhook_outbox_event`
- `provider_polling_request`
- `scheduled_scan_config`
- `scheduled_scan_run`

Definitions that map to existing persisted enums preserve the existing strings. Definitions for future objects are registry-only and do not create those product modules.

## Current Lifecycle Rules

`import_batch`

- States: `pending`, `processing`, `completed`, `completed_with_warnings`, `failed`, `cancelled`
- Terminal: `completed`, `completed_with_warnings`, `failed`, `cancelled`
- Main path: `pending -> processing -> completed`

`live_feed_subscription`

- States: `active`, `paused`, `failed`, `stopped`, `stale`
- Terminal: `stopped`
- Main paths: pause/resume, stale recovery, failure recovery, stop

`analysis_run`

- States: `queued`, `running`, `completed`, `failed`, `insufficient_data`, `cancelled`
- Terminal: `completed`
- Retry path: `failed`, `insufficient_data`, or `cancelled` can return to `queued`

`signal_classification`

- States: `signal`, `no_signal`, `unclear`, `insufficient_evidence`
- Terminal: all states
- This is an inspection-only result set, not a mutating workflow.

`outcome_evaluation`

- States: `pending`, `evaluated`, `insufficient_future_data`, `skipped_not_directional`, `failed`
- Terminal: `evaluated`, `insufficient_future_data`, `skipped_not_directional`, `failed`

`reasoning_run`

- States: `pending`, `completed`, `failed`, `blocked`, `fallback_used`, `provider_not_configured`
- Terminal: all states except `pending`

`reasoning_action_item`

- States: `pending`, `due`, `running`, `completed`, `skipped`, `failed`, `cancelled`
- Terminal: `completed`, `skipped`, `cancelled`
- Retry path: `failed -> due`

`operator_review_item`

- States: `open`, `acknowledged`, `dismissed`, `applied_manually`
- Terminal: `dismissed`, `applied_manually`
- Current mapping: calibration recommendation review statuses.

Future registry-only definitions:

- `dataset_export`
- `webhook_outbox_event`
- `provider_polling_request`
- `scheduled_scan_config`
- `scheduled_scan_run`

## API Contracts

List state machines:

```txt
GET /state-machines
GET /state-machines?objectType=analysis_run
GET /state-machines?status=active
```

Get a state machine:

```txt
GET /state-machines/{key}
GET /state-machines/{key}?version=1.0.0
```

Seed default definitions:

```txt
POST /state-machines/seed-default
```

Validate a transition:

```txt
POST /state-machines/validate-transition
```

Request:

```json
{
  "objectType": "analysis_run",
  "fromState": "queued",
  "toState": "running",
  "workspaceId": null,
  "objectId": null,
  "stateMachineKey": null,
  "stateMachineVersion": null,
  "recordValidation": true
}
```

Response:

```json
{
  "stateMachineKey": "analysis_run",
  "stateMachineVersion": "1.0.0",
  "objectType": "analysis_run",
  "objectId": null,
  "fromState": "queued",
  "toState": "running",
  "validationStatus": "valid",
  "isValid": true,
  "reason": "Transition is valid",
  "validationId": "00000000-0000-0000-0000-000000000000",
  "terminalTransition": false
}
```

If `recordValidation` is `false`, the service returns the validation result without inserting an audit row.

## Adoption Path

1. Keep existing service-level lifecycle writes unchanged.
2. Seed default state machines in each environment.
3. Use `GET /state-machines` for operator and documentation inspection.
4. Add `validate_transition(...)` calls to one service at a time before status mutation.
5. Record validations only where audit value justifies the write.
6. Keep database check constraints as the final guard for allowed status strings.

## Safety Boundaries

- The registry is descriptive and validation-oriented.
- It does not classify signals, evaluate outcomes, run reasoning, execute actions, send alerts, or call brokers.
- It does not provide financial advice.
- It does not auto-apply strategy, diagnostic, scan, provider polling, webhook, or retention behavior.
