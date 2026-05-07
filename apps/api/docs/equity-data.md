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
- `polygon`: registered provider skeleton using credential references.
- `alpaca`: data/research-only skeleton with no account, order, or position behavior.
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
GET /equity-data/operations/{operation_id}
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
EQUITY_DATA_ALLOW_EXTERNAL_REQUESTS=false
EQUITY_DATA_ENABLE_MOCK_PROVIDER=true
```

## Credential References

External providers use `credentialRefId` and the existing provider credential reference module.
Raw provider secrets are not accepted by equity data APIs, are not logged, and are not stored in
equity data tables. Request and provider reference payloads are redacted for keys such as token,
secret, api key, password, authorization, credential, private key, access key, and passwd.

The equity credential resolver returns readiness status only. Mock and CSV providers are ready
without credentials. Polygon, Alpaca, and generic HTTP remain not ready unless external requests and
a safe secret-resolution path are configured. This milestone does not expose raw secret material to
API responses.

## Intentionally Deferred

- Real Polygon/Alpaca network fetches remain deferred.
- Persistent raw upload storage is not implemented.
- Secret-manager value retrieval is not implemented unless a future safe secret provider is wired.
- External signal delivery, broker execution, auto-trading, copy trading, and financial-advice
  output remain outside the product boundary.

## Equity Research Integration

Equity swing scoring can read latest metadata, fundamentals, and earnings context when available.
Liquidity context can use metadata/fundamentals average volume when universe member volume is
missing. Evidence uses safe research language such as average volume context available, upcoming
earnings context available, and fundamentals context unavailable.
