# Symbol And Data Source Configuration Services

Phase 3 adds the first business-facing configuration APIs. It does not add candle imports, live provider connections, analysis execution, signals, indicators, pattern detection, news correlation, or LLM behavior.

## Symbols

Symbols define market instrument metadata used by later candle validation, pip/tick calculations, and analysis.

### Endpoints

```txt
POST /symbols
GET /symbols
GET /symbols/{symbol_id}
PATCH /symbols/{symbol_id}
```

### Create Payload

```json
{
  "symbol": "EURUSD",
  "displayName": "EUR/USD",
  "marketType": "forex",
  "baseAsset": "EUR",
  "quoteAsset": "USD",
  "pipSize": "0.0001",
  "tickSize": null,
  "pricePrecision": 10,
  "quantityPrecision": 10,
  "isActive": true
}
```

### Rules

- `symbol`, `base_asset`, and `quote_asset` are normalized to uppercase.
- `display_name` is trimmed.
- Forex symbols require `pip_size`.
- Crypto symbols require `tick_size`.
- `pip_size` and `tick_size` must be positive when supplied.
- Precision fields must be non-negative.
- Inactive symbols remain queryable but should not be accepted by future import or analysis workflows.

### Seed Definitions

Default seed definitions live in:

```txt
app/modules/symbols/seeds.py
```

Included symbols:

- `EURUSD`
- `GBPUSD`
- `USDJPY`
- `XAUUSD`
- `BTCUSDT`
- `ETHUSDT`

The seed module only defines typed payloads. It does not mutate the database automatically.

## Data Sources

Data sources define where market data originated. CSV imports, JSON imports, API polling, websocket live feeds, and manual seeds all flow through this configuration boundary.

### Endpoints

```txt
POST /data-sources
GET /data-sources
GET /data-sources/{data_source_id}
PATCH /data-sources/{data_source_id}
```

### Create Payload

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "name": "CSV Upload",
  "sourceType": "csv_upload",
  "provider": "csv",
  "status": "active",
  "configJson": {}
}
```

### Supported Source Types

- `csv_upload`
- `json_import`
- `api_polling`
- `websocket_live`
- `manual_seed`

### Supported Statuses

- `active`
- `inactive`
- `failed`

### Rules

- Data sources are workspace-scoped.
- `name` and `provider` are trimmed.
- `config_json` defaults to an empty object.
- Provider credentials must not be stored in `config_json`; use environment-managed secrets instead.
- Future import and live feed modules should reject inactive or failed sources.

### Seed Definitions

Default seed definitions live in:

```txt
app/modules/data_sources/seeds.py
```

The seed function requires a `workspace_id` and returns typed payloads for:

- CSV upload source
- Internal JSON import source

It does not mutate the database automatically.

## Error Shape

Domain errors use the standard API error envelope:

```json
{
  "error": {
    "code": "symbol_not_found",
    "message": "Symbol not found",
    "requestId": "request-id"
  }
}
```

Common codes:

- `symbol_not_found`
- `symbol_conflict`
- `invalid_symbol`
- `data_source_not_found`
- `data_source_conflict`

## Not Implemented In Phase 3

- Workspace management APIs
- User management APIs
- Seed execution command
- Auth and authorization
- CSV import parser
- JSON candle batch parser
- Live feed provider adapter
- Candle validation and upsert behavior
- Analysis run creation
- Trading intelligence engines
