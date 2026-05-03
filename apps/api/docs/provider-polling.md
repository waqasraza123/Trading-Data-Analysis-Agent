# Market Data Provider Polling

Provider polling adds backend-only retrieval of historical or recent OHLC candles from external
market data providers. It is data ingestion only.

It does not place orders, connect to brokers, execute trades, send alerts, provide UI behavior,
or produce financial advice.

## Module Layout

```txt
app/modules/provider_polling/
  models.py
  schemas.py
  repository.py
  service.py
  normalizer.py
  routes.py
  adapters/
    base.py
    mock.py
    binance_public_rest.py
    generic_ohlc_http.py
    registry.py
```

## Storage

Provider polling persists request audit state in:

```txt
provider_polling_requests
provider_polling_errors
```

Requests track provider, provider symbol, timeframe, requested time range, requested URL when safe
to store, metadata, received/stored/skipped candle counts, status, and completion timestamps.

Errors track request-level, adapter-level, validation, and candle conflict failures without storing
provider secrets.

## Source Boundary

Provider polling requires a `data_sources` row with:

```txt
source_type = api_polling
status = active
```

The source must belong to the requested workspace and the symbol must be active.

Existing `source_type` values are:

```txt
csv_upload
json_import
api_polling
websocket_live
manual_seed
chart_screenshot
```

## Shared Candle Path

The ingestion path is:

```txt
API request
-> provider_polling_requests row
-> provider adapter
-> ProviderCandle
-> NormalizedCandleInput
-> shared candle validator
-> shared candle repository
-> candles
-> provider_polling_requests counts and provider_polling_errors
```

Provider polling does not write directly to `candles` and does not bypass candle validation.

Final candle behavior remains owned by the shared candle repository:

- matching final candles are skipped as duplicates
- late partial candles after final candles are skipped
- partial candles can be finalized by later final candles
- conflicting final candles are not overwritten and are recorded as polling errors

## Providers

### `mock_polling`

Generates deterministic final candles for local development and tests. It does not perform network
calls and does not require credentials.

### `binance_public_rest`

Uses Binance public REST `/api/v3/klines` with no credentials. It supports the repository
timeframes that map directly to Binance intervals:

```txt
1m
5m
15m
30m
1h
4h
1d
```

The adapter uses the configured timeout, user agent, base URL, provider symbol, optional start/end
time, and limit. It stores only the public request URL and bounded metadata.

### `generic_ohlc_http`

Registered as a safe stub for future provider-specific mappings. It returns no candles and records
an explicit `generic_adapter_not_configured` error.

## Settings

```txt
PROVIDER_POLLING_TIMEOUT_SECONDS=20
PROVIDER_POLLING_MAX_CANDLES_PER_REQUEST=1000
PROVIDER_POLLING_USER_AGENT=trading-intelligence-api-provider-polling/0.1
BINANCE_PUBLIC_REST_BASE_URL=https://api.binance.com
```

No paid provider keys are required at startup.

## API

```txt
POST /provider-polling/requests
GET /provider-polling/requests
GET /provider-polling/requests/{request_id}
GET /provider-polling/requests/{request_id}/errors
```

Create request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "provider": "mock_polling",
  "providerSymbol": "BTCUSDT",
  "timeframe": "1m",
  "startTime": "2026-04-29T10:00:00Z",
  "endTime": "2026-04-29T10:30:00Z",
  "limit": 500
}
```

Request statuses:

```txt
pending
running
completed
completed_with_warnings
failed
```

## Secret Handling

Provider polling does not require secrets for v1 providers.

Request metadata rejects sensitive key names such as `api_key`, `token`, `secret`, `password`,
`authorization`, and related variants. Provider adapters must not place secrets in requested URLs,
metadata, error rows, or logs.

## Not Implemented

- broker integration
- order placement
- auto-trading
- alerts
- UI
- paid provider credentials
- background provider polling worker
- generic provider-specific mapping configuration
- websocket live feed runtime changes
- CSV/JSON import rewrites
## Integrated Engine Boundary

Provider polling stores normalized candles through the shared candle path. Those candles can later be
used by multi-timeframe aggregation, analysis, reports, and backtest experiments, but polling does not
run analysis, trigger scheduled scans, mutate signals, require provider secrets at startup, or interact
with broker execution.
