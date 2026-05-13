# Equity Data Provider Foundation

The equity data module adds provider-backed and manual foundations for stock universe import,
symbol metadata, fundamentals context, earnings events, and catalyst enrichment. It is market data
and research infrastructure only.

It does not place orders, connect to brokers for order execution, auto-trade, use LLM
classification, make certainty claims, or provide financial advice.

## Module Layout

```txt
app/modules/equity_data/
  models.py
  schemas.py
  repository.py
  service.py
  operations.py
  jobs.py
  csv_import.py
  credentials.py
  normalizer.py
  routes.py
  adapters/
```

Adapters expose a shared `EquityDataProvider` interface for universe import, metadata lookup,
fundamentals snapshots, and earnings calendars.

## Providers

- `mock_equity_data`: deterministic local provider for demos and tests.
- `csv_equity_import`: accepts JSON/CSV-like rows from the API.
- `polygon`: opt-in authenticated read-only provider for ticker reference, ticker overview,
  financial ratio snapshots, and earnings calendar context.
- `alpaca`: opt-in authenticated read-only provider for assets/universe discovery and asset
  metadata lookup. No account, order, position, or broker workflow endpoints are called.
- `generic_http`: future custom provider placeholder; it does not execute arbitrary URLs by default.

## Storage

The migration `202605071100_add_equity_data_foundation.py` adds:

- `equity_data_provider_requests`
- `equity_symbol_metadata_snapshots`
- `equity_fundamental_snapshots`
- `equity_earnings_events`
- `equity_data_import_errors`

The migration `202605071200_add_equity_data_operations.py` adds:

- `equity_data_operations`
- Job queue support for `equity_data.operation` on the `equity_data` queue

Provider requests track request type, status, provider, optional credential reference, counts,
bounded request metadata, bounded response summary, and safe errors.

Operations track background import/enrichment progress, counters, redacted request/result/error
summaries, optional linked provider request, optional linked queue job, and dry-run status.

## API

```txt
GET /equity-data/providers
POST /equity-data/providers/{provider}/test
POST /equity-data/universe-import/rows
POST /equity-data/universe-import/provider
GET /equity-data/provider-requests
GET /equity-data/provider-requests/{request_id}
GET /equity-data/provider-requests/{request_id}/errors
POST /equity-data/symbols/{symbol_id}/metadata/lookup
GET /equity-data/symbols/{symbol_id}/metadata/latest
POST /equity-data/symbols/{symbol_id}/fundamentals/fetch
GET /equity-data/symbols/{symbol_id}/fundamentals/latest
POST /equity-data/symbols/{symbol_id}/earnings/fetch
GET /equity-data/symbols/{symbol_id}/earnings
POST /equity-data/earnings/import-rows
POST /equity-data/earnings/{event_id}/create-catalyst-context
GET /equity-data/operations
GET /equity-data/operations/summary
GET /equity-data/operations/review-queue
GET /equity-data/operations/{operation_id}
GET /equity-data/operations/{operation_id}/diagnostics
GET /equity-data/operations/{operation_id}/lineage
GET /equity-data/operations/{operation_id}/audit-bundle
POST /equity-data/operations/{operation_id}/cancel
POST /equity-data/operations/{operation_id}/retry
POST /equity-data/operations/universe-import
POST /equity-data/operations/universe-import-file
POST /equity-data/operations/metadata-enrichment
POST /equity-data/operations/fundamentals-enrichment
POST /equity-data/operations/earnings-enrichment
POST /equity-data/operations/earnings-to-catalysts
```

## Universe Import

Universe imports require `workspaceId`. A request can target an existing `universeId` or provide
`createUniverseName` to create a new equity universe. Tickers are normalized uppercase, missing
stock symbols are created as `market_type=stock`, duplicate universe membership is reactivated and
updated, and metadata snapshots are stored when row/provider metadata is available.

## Background Operations

Equity data operations wrap larger imports and enrichment work while preserving the existing
provider request history. Supported operation types are:

- `universe_import_rows`
- `universe_import_file`
- `provider_universe_import`
- `metadata_enrichment`
- `fundamentals_enrichment`
- `earnings_enrichment`
- `earnings_to_catalysts`

Statuses follow the existing job queue vocabulary: `pending`, `running`, `completed`,
`completed_with_warnings`, `failed`, and `cancelled`. The worker entrypoint is the existing job
queue worker:

```txt
python -m app.workers.job_queue_worker --queue equity_data
```

Small row imports can run synchronously. Larger imports and enrichment requests can be queued and
will update operation progress and counters as the worker runs.

`GET /equity-data/operations/summary` returns workspace-scoped operational rollups for the equity
data queue: total operations, active operations, terminal operations, warning, failed, and cancelled
counts, grouped status/type/provider counts, the latest operation timestamp, and a bounded list of
recent warning/failed/cancelled operations. It reads only `equity_data_operations` and does not
claim jobs, retry work, cancel work, call providers, or mutate artifacts.

`GET /equity-data/operations/review-queue` returns a bounded workspace review queue for operations
that need operator attention. It includes failed, warning, cancelled, and stale pending/running
operations, plus a review reason, severity, safe recommended action, retry eligibility, stop
eligibility, and last update timestamp. Stale detection is read-only and controlled by the
`stale_after_minutes` query parameter. The endpoint does not stop, retry, claim, or enqueue work.

`GET /equity-data/operations/{operation_id}/diagnostics` composes a bounded operator diagnostic
view from existing persisted records. The response includes the operation, linked job queue item,
linked job events, linked provider request, recent import errors, and a chronological timeline
covering operation, job, provider request, and row-error events. It does not create events, claim or
retry jobs, cancel work, call external providers, expose raw provider secrets, or mutate artifacts.

`GET /equity-data/operations/{operation_id}/lineage` composes retry lineage from existing operation
request summaries. It returns the selected operation, root operation, source chain, downstream retry
operations, and a bounded tree of lineage nodes. The endpoint scans a bounded recent workspace
operation window controlled by `scan_limit`; it may omit very old retry siblings outside that
window, but it still fetches direct source ancestors by id when present. It does not create retry
records, enqueue jobs, execute work, call providers, or mutate artifacts.

`GET /equity-data/operations/{operation_id}/audit-bundle` returns a single read-only operator audit
package for the selected operation. The package includes operation detail, recent import errors,
diagnostics, retry lineage, an optional review-queue item, and section summaries with bounded
`error_limit`, `scan_limit`, and `stale_after_minutes` controls. It exists for cockpit review and
documentation handoff only; it does not retry, cancel, enqueue, claim jobs, call providers, expose
secrets, mutate artifacts, or provide financial advice.

Operation submission accepts optional `idempotencyKey` values on JSON operation requests. Repeating
the same workspace key returns the existing operation when the operation type, provider, and dry-run
mode match. Reusing the key for a different operation returns a conflict instead of creating
ambiguous duplicate work.

Operations can be cancelled through `POST /equity-data/operations/{operation_id}/cancel` with an
optional `reason`. Cancellation is idempotent for terminal operations. For queued work, the linked
job queue item is cancelled in the same transaction when present. Running enrichment and catalyst
conversion operations check the operation status between item-level steps and stop cooperatively
when an operator cancels the operation. Already persisted provider requests, snapshots, earnings
events, or catalyst contexts are retained as audit artifacts; cancellation does not roll back prior
successful item writes and does not execute provider, broker, notification, or trading workflows.

Operations can be retried through `POST /equity-data/operations/{operation_id}/retry` when the
source operation is `completed_with_warnings`, `failed`, or `cancelled`. Retry creates a new
operation record and enqueues or synchronously runs it from the persisted request payload; the
source operation remains unchanged as audit history. The request accepts optional `runMode`,
`idempotencyKey`, and `reason` fields. When an idempotency key is supplied, reuse is scoped to the
new retry operation type, provider, workspace, and dry-run mode. Retry is intentionally rejected
when the operation only has a compacted request summary, such as a row import whose original row
payload is no longer present in the linked job payload. The endpoint does not roll back prior
artifacts, restore cancelled jobs, execute broker workflows, send alerts, or bypass provider
credential readiness checks.

## CSV File Imports

`POST /equity-data/operations/universe-import-file` accepts `multipart/form-data` with:

- `workspace_id`
- `file`
- optional `universe_id`
- optional `create_universe_name`
- optional `provider_name`, default `csv_equity_import`
- optional `run_mode`: `auto`, `sync`, or `queued`
- optional `dry_run`

CSV parsing is UTF-8 with BOM handling. Supported headers are `ticker` or `symbol`, plus optional
`name`, `exchange`, `sector`, `industry`, `currency`, `country`, `asset_type`, `market_cap`,
`average_volume`, `shares_float`, `is_etf`, and `is_active`. Unknown columns are ignored for import;
credential-shaped columns are redacted before summaries or row-level errors are stored.

No raw uploaded file bytes are persisted. In queued mode, the request parses and validates the file
first, then stores sanitized row payloads in queue metadata up to
`EQUITY_DATA_MAX_QUEUED_IMPORT_ROWS`. Files beyond the configured safe staging limits are rejected
with a typed validation error.

## Fundamentals and Earnings

Fundamentals snapshots store contextual metrics such as market cap, average volume, relative
volume, beta, P/E, EPS, growth fields, debt-to-equity, and free cash flow when supplied by a
provider.

Earnings events store scheduled, estimated, reported, or unknown event status. Events can be
converted into existing `equity_catalyst_contexts` with `catalyst_type=earnings` and
`sentiment=unknown`. Catalyst summaries avoid causation language.

## Settings

```txt
EQUITY_DATA_VERSION=v1
EQUITY_DATA_DEFAULT_PROVIDER=mock_equity_data
EQUITY_DATA_MAX_UNIVERSE_IMPORT_ROWS=5000
EQUITY_DATA_SYNC_IMPORT_ROW_THRESHOLD=250
EQUITY_DATA_MAX_QUEUED_IMPORT_ROWS=5000
EQUITY_DATA_MAX_METADATA_LOOKUPS=1000
EQUITY_DATA_PROVIDER_TIMEOUT_SECONDS=20
EQUITY_DATA_PROVIDER_RETRY_ATTEMPTS=2
EQUITY_DATA_PROVIDER_RETRY_BACKOFF_SECONDS=0.75
EQUITY_DATA_PROVIDER_MAX_PAGES=3
EQUITY_DATA_ALLOW_EXTERNAL_REQUESTS=false
EQUITY_DATA_ENABLE_MOCK_PROVIDER=true
EQUITY_DATA_ENV_SECRET_RESOLUTION_ENABLED=false
POLYGON_REST_BASE_URL=https://api.polygon.io
ALPACA_TRADING_BASE_URL=https://paper-api.alpaca.markets
```

## Credential References

External providers use `credentialRefId` and the existing provider credential reference module.
Raw provider secrets are not accepted by equity data APIs, are not logged, and are not stored in
equity data tables. Request and provider reference payloads are redacted for keys such as token,
secret, api key, password, authorization, credential, private key, access key, and passwd.

The environment secret resolver is disabled by default. To enable real read-only Polygon or Alpaca
requests, configure both:

```txt
EQUITY_DATA_ALLOW_EXTERNAL_REQUESTS=true
EQUITY_DATA_ENV_SECRET_RESOLUTION_ENABLED=true
```

Credential references can point at environment-managed secret material with these `secret_ref`
formats:

- `env:POLYGON_API_KEY`: single environment value, mapped to `api_key`.
- `env-json:POLYGON_EQUITY_DATA_SECRET`: JSON object with `api_key` or `apiKey`.
- `env-json:ALPACA_EQUITY_DATA_SECRET`: JSON object with `api_key_id`/`api_secret_key`,
  `key_id`/`secret_key`, or Alpaca header-style keys.
- `env-pair:ALPACA_API_KEY_ID,ALPACA_API_SECRET_KEY`: two environment variables mapped to
  Alpaca API key id and secret key.

Resolved secret values are passed only to provider adapters in memory. They are not returned by
API responses, not written into provider request summaries, not stored in operation payloads, and
not copied into import error rows.

Polygon calls are limited to read-only market/reference data:

- `GET /v3/reference/tickers`
- `GET /v3/reference/tickers/{ticker}`
- `GET /stocks/financials/v1/ratios`
- `GET /benzinga/v1/earnings`

Polygon universe imports follow Polygon cursor pagination through the `cursor` query parameter only.
They never follow arbitrary provider URLs directly. Pagination is bounded by
`EQUITY_DATA_PROVIDER_MAX_PAGES`; callers can request a lower `filters.maxPages`/`filters.max_pages`
value for a smaller import. When a provider has more pages than the configured limit, the request
completes with a `polygon_pagination_truncated` warning and records `truncated=true` in the response
summary.

Alpaca calls are limited to read-only asset metadata:

- `GET /v2/assets`
- `GET /v2/assets/{symbol}`

Provider responses are normalized into the existing symbol metadata, fundamentals, earnings, and
universe storage contracts. Unsupported plans, provider HTTP errors, invalid JSON, missing secret
material, or incomplete credentials are persisted as typed provider request or operation failures
without exposing raw credentials.

Provider HTTP requests retry transient `429` and `5xx` responses with bounded exponential backoff.
`Retry-After` is honored up to 60 seconds when present. Request URLs, authorization headers, query
API keys, and secret values are not written into provider request summaries or operation records.

## Intentionally Deferred

- Persistent raw upload storage is not implemented.
- Managed secret-manager value retrieval beyond environment-backed secret references is not
  implemented.
- Alpaca fundamentals and earnings imports are not implemented because the current adapter uses only
  the read-only assets surface.
- External signal delivery, broker execution, auto-trading, copy trading, and financial-advice
  output remain outside the product boundary.

## Equity Research Integration

Equity swing scoring can read latest metadata, fundamentals, and earnings context when available.
Liquidity context can use metadata/fundamentals average volume when universe member volume is
missing. Evidence uses safe research language such as average volume context available, upcoming
earnings context available, and fundamentals context unavailable.
