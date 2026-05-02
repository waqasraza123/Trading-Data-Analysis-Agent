# Market Watchlists And Scheduled Scans

Market scans add backend watchlists and bounded due analysis runs over already-stored candle data.
They do not add UI, alerts, notifications, broker execution, auto-trading, copy trading, external
market data provider integration, billing, or financial-advice output.

## Scope

Implemented:

```txt
market watchlists
watchlist symbol/timeframe items
single-symbol scheduled scan configs
watchlist scheduled scan configs
due scan listing
manual scan execution
bounded due scan execution
scheduled scan runs
per-item scan results
optional worker entrypoint
```

Scheduled scans create deterministic backend analysis runs from stored candles. Final candles remain
the default source of truth. Partial live candles are included only when a watchlist item or scan
config explicitly sets `include_partial_live_candle=true` and the existing analysis lifecycle can
support that window.

## API Endpoints

```txt
POST /market-watchlists
GET /market-watchlists
GET /market-watchlists/{watchlist_id}
PATCH /market-watchlists/{watchlist_id}
POST /market-watchlists/{watchlist_id}/items
GET /market-watchlists/{watchlist_id}/items
PATCH /market-watchlist-items/{item_id}
DELETE /market-watchlist-items/{item_id}

POST /scheduled-scan-configs
GET /scheduled-scan-configs
GET /scheduled-scan-configs/due
POST /scheduled-scan-configs/run-due
GET /scheduled-scan-configs/{scan_config_id}
PATCH /scheduled-scan-configs/{scan_config_id}
POST /scheduled-scan-configs/{scan_config_id}/pause
POST /scheduled-scan-configs/{scan_config_id}/resume
POST /scheduled-scan-configs/{scan_config_id}/archive
POST /scheduled-scan-configs/{scan_config_id}/run

GET /scheduled-scan-runs/{scan_run_id}
GET /scheduled-scan-runs/{scan_run_id}/items
```

## Watchlists

Watchlists are workspace-scoped groups of symbol/timeframe scan items.

Status values:

```txt
active
paused
archived
```

Only active watchlists are scanned. Paused or archived watchlists are skipped and do not create
analysis work.

Watchlist items require:

```txt
symbol_id
timeframe
```

Optional item fields:

```txt
source_id
include_partial_live_candle
metadata_json
```

Symbols must exist and be active. A provided source must exist, belong to the same workspace, and be
active. Duplicate item identity is rejected for the same watchlist, symbol, source, and timeframe.
Deleting an item deactivates it so prior scan runs keep their historical context.

## Scheduled Scan Configs

Scan modes:

```txt
watchlist
single_symbol
```

Watchlist mode requires `watchlist_id`. Single-symbol mode requires `symbol_id` and `timeframe`.
`lookback_minutes` and `interval_seconds` must be positive. When omitted on create, defaults come
from:

```txt
MARKET_SCAN_DEFAULT_LOOKBACK_MINUTES=60
MARKET_SCAN_DEFAULT_INTERVAL_SECONDS=60
```

Config status values:

```txt
active
paused
archived
```

Only active configs with `next_run_at <= now` are due. Paused and archived configs are not due.
Resuming a config calculates `next_run_at` when it is missing.

## Scan Execution

A scan run stores aggregate counts and the analysis, signal, reasoning, and action-plan ids created
by the run. A scan item stores per-symbol status and optional artifact ids.

For each scan item:

```txt
resolve symbol/timeframe/source
load latest final candle unless partial candles are explicitly enabled
calculate end_time from latest eligible candle
calculate start_time = end_time - lookback_minutes
check window quality
create deterministic analysis run with analysis_mode=scheduled_scan
store signal_id when deterministic classification produces a signal
optionally create scenario reasoning when enabled and configured
optionally create an action plan only from a reasoning run
```

Scan runs and per-item rows are traceability artifacts. Audit timelines can show which scan created
an analysis run or signal, intelligence reports can reference scan source metadata, and quality
gates can inspect scan-created signals without mutating them.

Skipped reasons include:

```txt
watchlist_paused
scan_config_paused
no_active_watchlist_items
missing_candles
insufficient_candles
analysis_failed
reasoning_disabled
reasoning_unavailable
action_plan_unavailable
unsupported_scan_mode
```

After a scan run completes, active configs set:

```txt
last_run_at = now
next_run_at = now + interval_seconds
```

If a run is already pending or running for a config, another run request returns that existing run
instead of starting duplicate work.

## Worker

The optional worker entrypoint is:

```sh
MARKET_SCAN_WORKER_ENABLED=true .venv/bin/python -m app.workers.market_scan_worker
```

Worker settings:

```txt
MARKET_SCAN_WORKER_ENABLED=false
MARKET_SCAN_WORKER_POLL_SECONDS=30
MARKET_SCAN_WORKER_BATCH_SIZE=10
MARKET_SCAN_DEFAULT_LOOKBACK_MINUTES=60
MARKET_SCAN_DEFAULT_INTERVAL_SECONDS=60
```

The worker polls due scan configs, runs a bounded batch, sleeps, and stops gracefully on process
signals. The worker does not send notifications, execute reasoning action items, call brokers, or
fetch external market data.

The supervisor can include the component with:

```sh
WORKER_SUPERVISOR_COMPONENTS=market_scans MARKET_SCAN_WORKER_ENABLED=true \
.venv/bin/python -m app.workers.supervisor
```

## Safety

Market scans do not:

```txt
send alerts or notifications
execute broker actions
place orders
auto-trade
copy trade
provide financial advice
fetch external market data
override deterministic signals with LLM output
```

LLM scenario reasoning remains optional and downstream of deterministic artifacts. LLM output never
classifies or overrides signals. Action plans remain backend-safe follow-up records and are not
executed by the market scan worker.
