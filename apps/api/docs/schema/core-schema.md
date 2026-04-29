# Core Database Schema

Phase 2 establishes the first production database boundary for the backend. It does not add routes, imports, live feed connections, analysis execution, indicators, signals, or LLM behavior.

## Source Of Truth

`candles` is the normalized market data truth table.

Both historical imports and live feed ingestion must eventually write into `candles` through one validation and normalization path:

- Historical CSV/JSON imports link candles with `import_batch_id`.
- Live feed events link candles with `live_feed_event_id`.
- API polling and manual seed sources still use `source_id`.
- Analysis should use `is_final = true` by default.
- Partial live candles are stored with `is_final = false` and must be included only when explicitly requested by a live analysis mode.

## Tables Added

### `workspaces`

Workspace boundary for future multi-tenant isolation.

Important fields:

- `id`
- `name`
- `created_at`
- `updated_at`

### `users`

Users are scoped to a workspace and have one of:

- `admin`
- `user`
- `analyst`

The schema enforces unique email per workspace.

### `symbols`

Market instrument metadata used later for pip/tick logic.

Allowed `market_type` values:

- `forex`
- `crypto`
- `stock`
- `index`
- `commodity`

The schema enforces positive `pip_size` and `tick_size` when present.

### `data_sources`

Tracks both batch and live data origins.

Allowed `source_type` values:

- `csv_upload`
- `json_import`
- `api_polling`
- `websocket_live`
- `manual_seed`

Allowed `status` values:

- `active`
- `inactive`
- `failed`

### `import_batches`

Tracks CSV/JSON batch ingestion metadata. This is not the importer implementation.

Important fields:

- row counts
- duplicate count
- missing candle count
- quality score
- error summary
- start/completion timestamps

### `import_errors`

Stores row-level import validation failures for future CSV/JSON import workflows.

### `live_feed_subscriptions`

Tracks live market data subscription state.

Allowed statuses:

- `active`
- `paused`
- `failed`
- `stopped`
- `stale`

### `live_feed_events`

Stores raw provider event metadata for audit before normalization.

Allowed event types:

- `candle_partial`
- `candle_final`
- `heartbeat`
- `reconnect`
- `error`
- `snapshot`

Allowed processing statuses:

- `received`
- `processed`
- `ignored`
- `failed`

### `candles`

Normalized market data table shared by all ingestion paths.

Important constraints:

- `open`, `high`, `low`, and `close` must be positive.
- `high >= open`
- `high >= close`
- `high >= low`
- `low <= open`
- `low <= close`
- `volume` must be non-negative when present.
- `quality_score` must be between 0 and 1 when present.
- Uniqueness is enforced on `workspace_id`, `symbol_id`, `source_id`, `timeframe`, and `timestamp`.

Important indexes:

- `workspace_id`, `symbol_id`, `timeframe`, `timestamp`
- `workspace_id`, `symbol_id`, `timeframe`, `timestamp`, `is_final`
- `source_id`, `timestamp`
- `import_batch_id`
- `live_feed_event_id`

### `analysis_runs`

Tracks future historical, live-window, scheduled, and replay analysis requests.

Allowed analysis modes:

- `historical`
- `live_window`
- `scheduled_scan`
- `replay`

Allowed statuses:

- `queued`
- `running`
- `completed`
- `failed`
- `insufficient_data`
- `cancelled`

`include_partial_live_candle` defaults to false.

### `analysis_audit_logs`

Stores future analysis lifecycle audit events.

### `engine_versions`

Stores deterministic engine versions and configuration snapshots for future replay and audit.

## Migration

The initial schema migration is:

```txt
apps/api/alembic/versions/202604290620_core_database_schema.py
```

It is intentionally hand-written so the first schema captures the exact Phase 2 boundaries.

## Not Implemented In Phase 2

- API routes for these tables
- repositories
- services
- seed data
- CSV parsing
- live provider adapters
- candle normalizer
- candle upsert behavior
- analysis workers
- feature/indicator/pattern/signal engines
- explanations
- news correlation
