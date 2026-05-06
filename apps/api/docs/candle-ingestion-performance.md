# Candle Ingestion Performance

The candle ingestion performance layer adds measurable, chunked storage for high-volume candle
imports and provider polling batches. It is backend-only and preserves existing candle validation,
final/partial storage rules, and analysis semantics.

## Settings

- `CANDLE_INGESTION_BATCH_SIZE`, default `5000`: number of normalized rows processed per database
  batch.
- `CANDLE_INGESTION_MAX_ROWS_PER_REQUEST`, default `250000`: hard limit for one import request.
- `CANDLE_INGESTION_ENABLE_COPY_PATH`, default `false`: reserved interface for a future COPY-style
  write path. The current implementation records the setting in diagnostics but always uses the
  safe SQLAlchemy batch path.
- `CANDLE_INGESTION_PROGRESS_EVERY_ROWS`, default `10000`: row interval for flushing progress to
  the performance run record.

## Target Behavior

The default path is designed for 10k and 100k candle workloads by validating rows in chunks,
prefetching existing candles by unique key per chunk, and applying inserts/updates without one
database lookup per row. CSV parsing can stream parsed rows through the service instead of keeping
all parsed rows in memory.

## Conflict Semantics

Existing candle source-of-truth rules remain unchanged:

- Final candles are not overwritten by later partial candles.
- Matching final candles are skipped as duplicates.
- Conflicting final candles are rejected and reported.
- Existing partial candles can be updated or finalized.
- Validation is not bypassed.

Conflicts are persisted to `candle_ingestion_conflicts` with the existing candle payload when
available, the incoming candle payload, conflict type, and resolution. Duplicate finals and partial
after final rows are visible in diagnostics without changing stored final candles.

## API

```txt
GET /candle-ingestion/performance-runs?workspace_id={workspace_id}
GET /candle-ingestion/performance-runs/{run_id}
GET /candle-ingestion/performance-runs/{run_id}/conflicts
```

Performance runs include received, validated, inserted, updated, duplicate-skipped, conflicted,
failed, batch count, elapsed milliseconds, and diagnostics JSON.

## Import And Provider Integration

Existing `/imports/candles/json`, `/imports/candles/csv`, and `/provider-polling/requests` paths
create performance runs when they store candles. Existing import batch and provider polling error
contracts are preserved so downstream callers do not need a new ingestion API.

## Safety Boundary

This layer does not execute brokers, auto-trade, send trading alerts, change deterministic analysis,
or provide financial advice. Final candles remain the default analysis input, and partial candles
remain explicit.
