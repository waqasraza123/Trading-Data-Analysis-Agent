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

Replay metadata is stored directly on replay runs:

- `replayed_from_analysis_run_id`
- `replay_mode`

Allowed replay modes:

- `latest_engine_version`
- `same_engine_version`

### `analysis_audit_logs`

Stores future analysis lifecycle audit events.

### `engine_versions`

Stores deterministic engine versions and configuration snapshots for future replay and audit.

### `feature_snapshots`

Stores deterministic feature artifacts for completed analysis runs.

### `indicator_snapshots`

Stores deterministic indicator artifacts for completed analysis runs.

### `pattern_candidates`

Stores every deterministic pattern candidate considered for an analysis run.

Allowed bias values:

- `bullish`
- `bearish`
- `neutral`

`strength_score` is constrained from 0 to 1. One candidate may be marked selected when a detector score clears the current selection threshold.

### `strategy_profiles`

Stores deterministic analysis profile configuration for signal classification.

Important fields:

- `key`
- `version`
- `is_active`
- allowed and excluded pattern JSON
- minimum candidate strength and confidence
- component weights
- risk filters
- no-signal rules

`key` and `version` are unique together. Default profiles are seeded for breakout/continuation, reversal/rejection, range/chop avoidance, and fakeout protection.

### `signals`

Stores one current deterministic classification output per analysis run.

Important fields:

- analysis run, workspace, symbol, and timeframe
- selected strategy profile id/key/version and config snapshot
- classification status, bias, pattern type, confidence score, and confidence label
- selected pattern candidate id
- movement, volatility, trend, and range state fields
- summary and stable no-signal reason

Allowed statuses:

- `signal`
- `no_signal`
- `unclear`
- `insufficient_evidence`

Allowed bias values:

- `bullish`
- `bearish`
- `neutral`
- `unclear`

### `signal_confidence_components`

Stores every weighted confidence component for the selected signal output.

Components currently include:

- `pattern_strength`
- `trend_alignment`
- `volatility_confirmation`
- `indicator_support`
- `data_quality`

### `signal_evidence`

Stores deterministic signal evidence copied from selected pattern candidate evidence and classifier/conflict reasons.

### `signal_risk_notes`

Stores normalized risk and no-signal notes from candidate risk notes and deterministic classifier rules.

### `news_events`

Stores manual/imported market, economic, crypto, earnings, central-bank, and generic news events.
Events can be global or scoped to a workspace and can map by currency, asset, or symbol id.

### `signal_news_correlations`

Stores deterministic context linking completed signals to nearby relevant news events. Rows include
component scores, cautious reason text, scorer version metadata, and event-window configuration.
These rows do not override signal classification or confidence.

### `deterministic_explanations`

Stores one current safe deterministic explanation per signal. The row includes explanation sections, source artifact snapshots, safety status, and blocked terms when fallback text is used.

### `llm_explanations`

Stores one current optional grounded LLM explanation per signal, provider, model, and prompt version. Rows include the grounded input snapshot when enabled, safe output text or fallback text, safety status, blocked terms, grounding status, grounding issues, provider token metadata, optional estimated cost, and provider error metadata. The table is idempotent on `signal_id`, `provider`, `model`, and `prompt_version`.

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
