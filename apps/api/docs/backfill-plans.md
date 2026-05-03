# Backfill Plans

Backfill plans are safe planning records for bounded recomputation or generation of derived intelligence artifacts. They answer what would be eligible for later manual execution without running the work automatically.

This layer creates only:

```txt
intelligence_backfill_plans
intelligence_backfill_items
```

It does not mutate source artifacts, call external providers, start workers, send notifications, place broker orders, or provide financial advice.

## Purpose

Backfill planning helps operators inspect historical coverage before deciding whether to run explicit batches later:

- signals missing outcome evaluations
- completed analysis runs missing context-like artifacts
- signals or analysis runs eligible for module-specific derived artifacts
- stale-artifact requests when an artifact graph exists in a future phase
- bounded record counts before execution
- idempotent work-item contracts for later workers

## Dry Run

`dryRun` defaults to `true`. A dry run still persists the plan and its items so operators can inspect the exact bounded batch. It does not execute items.

Items remain in `planned`, `blocked`, or `skipped` state. Execution remains a future explicit/manual concern.

## Bounded Plans

Every plan uses a bounded limit. The request limit is read from `filters.limit`; when omitted the API uses:

```txt
BACKFILL_PLAN_DEFAULT_LIMIT=1000
BACKFILL_PLAN_MAX_LIMIT=10000
BACKFILL_PLAN_VERSION=v1
```

Requests above `BACKFILL_PLAN_MAX_LIMIT` fail before scanning. Planner queries always apply a limit and order by stable stored identifiers.

## Supported Operations

```txt
outcomes.evaluate
market_regime.generate
market_session.generate
advanced_features.generate
historical_case_vector.generate
reproducibility_manifest.generate
decision_readiness.assess
intelligence_quality.run
data_quality.run
confidence_calibration.run
```

If a target module is not implemented in the backend yet, the planner records eligible items as `blocked` with `module_unavailable`. `stale_artifacts` plans are blocked with `artifact_graph_unavailable` until an artifact graph exists.

## APIs

```txt
POST /backfill-plans
GET /backfill-plans
GET /backfill-plans/{plan_id}
GET /backfill-plans/{plan_id}/items
POST /backfill-plans/{plan_id}/cancel
```

Create request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "planType": "missing_artifacts",
  "targetModule": "outcomes",
  "targetOperation": "outcomes.evaluate",
  "filters": {
    "symbolId": null,
    "timeframe": null,
    "startTime": null,
    "endTime": null,
    "limit": 1000
  },
  "dryRun": true,
  "createExecutionRecords": false
}
```

The response includes eligible, planned, skipped, and blocked counts. Item responses include target type, target id, operation, status, priority, input contract, skip reason, block reason, optional execution record id, and result payload.

## Execution Contract

Backfill items are worker-ready contracts, not worker instructions that run automatically. A future worker can use each item as a bounded batch input:

- `targetType`
- `targetId`
- `targetOperation`
- `inputJson`
- `idempotencyKey`
- `status`

`createExecutionRecords=true` is accepted as a request flag, but no execution registry exists in this backend phase. The planner records `executionRegistryStatus=execution_registry_unavailable` in plan metadata and leaves items unqueued.

## Safety Boundaries

Backfill planning must remain backend-only and operator-driven:

- no automatic execution
- no scheduler
- no broker execution
- no auto-trading
- no alerts or notifications
- no external provider calls by default
- no source artifact mutation
- no financial advice

## Future Worker Integration

A future worker can claim `planned` items explicitly, create execution records if an execution registry exists, process bounded batches, and update item result state. That worker should preserve the same limits, idempotency keys, and source-artifact immutability rules.
