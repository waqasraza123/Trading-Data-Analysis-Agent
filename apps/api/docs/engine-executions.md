# Engine Execution Registry

The engine execution registry is a shared backend tracking layer for intelligence operations. It
records what engine task was requested, the input snapshot used, idempotency identity, status,
attempt count, produced artifacts, errors, and worker-claim fields.

It is not a broker, order, position, auto-trading, alerting, or financial-advice workflow. It does
not run tasks automatically and does not introduce Celery, Temporal, or external orchestration.

## Purpose

Backend modules can use execution records to make intelligence operations traceable and ready for
future worker orchestration without refactoring every module immediately.

Expected operation types include:

```txt
analysis.run
replay.run
outcomes.evaluate
reasoning.generate
action_item.execute
market_scan.run
profile_diagnostics.run
data_quality.run
provider_polling.run
event_study.run
dataset_export.build
profile_simulation.run
```

## Records

`engine_execution_records` stores:

- workspace and engine identity
- operation type and idempotency key
- pending/running/completed/failed lifecycle state
- priority
- optional source type and source id
- input snapshot
- output and produced artifacts
- error code/message
- attempts, max attempts, and lock fields
- started/completed/created/updated timestamps

Status values:

```txt
pending
running
completed
completed_with_warnings
skipped
failed
cancelled
```

Priority values:

```txt
low
normal
high
```

## Events

`engine_execution_events` stores append-only lifecycle messages for each record.

Event types:

```txt
created
claimed
started
completed
skipped
failed
retry_scheduled
cancelled
artifact_recorded
```

## Idempotency

`workspace_id` plus `idempotency_key` is unique. Creating a record with the same pair returns the
existing record by default. A force create option creates a separate record by deriving a new
idempotency key with a forced suffix.

Use stable keys derived from the backend operation and immutable input identity, for example:

```txt
analysis.run:{analysis_run_id}
replay.run:{original_analysis_run_id}:{mode}:{engine_version}
outcomes.evaluate:{signal_id}:{horizon_minutes}:{version}
reasoning.generate:{signal_id}:{reasoning_type}:{provider}:{model}
market_scan.run:{workspace_id}:{scan_config_hash}
```

## Claiming

The registry has worker-ready lock fields but does not create a worker in this phase.

Future workers can call `claim_pending_records(...)` to select pending records or stale running
records with expired locks. Claiming sets:

```txt
status=running
attempts=attempts+1
locked_by=<worker_id>
locked_until=now + ENGINE_EXECUTION_LOCK_SECONDS
started_at=<first claim time>
```

Claiming uses database row locks with skip-locked semantics so multiple future workers can safely
pick up different records.

## Settings

```txt
ENGINE_EXECUTION_DEFAULT_MAX_ATTEMPTS=3
ENGINE_EXECUTION_LOCK_SECONDS=120
ENGINE_EXECUTION_DEFAULT_PRIORITY=normal
```

## APIs

```txt
POST /engine-executions
GET /engine-executions
GET /engine-executions/{record_id}
GET /engine-executions/{record_id}/events
POST /engine-executions/{record_id}/cancel
```

Create request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "engineName": "analysis_lifecycle",
  "engineVersion": "analysis_lifecycle_0.1.0",
  "operationType": "analysis.run",
  "idempotencyKey": "analysis.run:00000000-0000-0000-0000-000000000000",
  "priority": "normal",
  "sourceType": "analysis_run",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "inputJson": {
    "timeframe": "15m"
  }
}
```

List filters:

```txt
workspace_id
status
engine_name
operation_type
source_type
source_id
limit
offset
```

## Integration Helpers

`EngineOperationRegistry` exposes lightweight helpers:

```python
await registry.record_analysis_operation(...)
await registry.record_replay_operation(...)
await registry.record_outcome_operation(...)
await registry.record_reasoning_operation(...)
await registry.record_scan_operation(...)
```

These helpers only create optional tracking records. Existing modules do not need to migrate in this
phase, and current worker behavior is unchanged. Callers that already manage a transaction can pass
`commit=False`.

## Boundaries

The registry records backend intelligence operation state. It must not become:

- broker workflows
- order workflows
- auto-trading
- alert dispatch
- financial advice
- external orchestration
