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

Provider requests track request type, status, provider, optional credential reference, counts,
bounded request metadata, bounded response summary, and safe errors.

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
```

## Universe Import

Universe imports require `workspaceId`. A request can target an existing `universeId` or provide
`createUniverseName` to create a new equity universe. Tickers are normalized uppercase, missing
stock symbols are created as `market_type=stock`, duplicate universe membership is reactivated and
updated, and metadata snapshots are stored when row/provider metadata is available.

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
EQUITY_DATA_MAX_METADATA_LOOKUPS=1000
EQUITY_DATA_PROVIDER_TIMEOUT_SECONDS=20
EQUITY_DATA_ALLOW_EXTERNAL_REQUESTS=false
EQUITY_DATA_ENABLE_MOCK_PROVIDER=true
```

## Credential References

External providers use `credentialRefId` and the existing provider credential reference module.
Raw provider secrets are not accepted by equity data APIs, are not logged, and are not stored in
equity data tables. Request and provider reference payloads are redacted for keys such as token,
secret, api key, password, authorization, and credential.

## Equity Research Integration

Equity swing scoring can read latest metadata, fundamentals, and earnings context when available.
Liquidity context can use metadata/fundamentals average volume when universe member volume is
missing. Evidence uses safe research language such as average volume context available, upcoming
earnings context available, and fundamentals context unavailable.
