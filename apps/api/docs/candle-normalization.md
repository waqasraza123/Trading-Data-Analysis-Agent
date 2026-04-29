# Candle Validation And Normalization Layer

This slice adds reusable internal code for normalized candle handling. It does not add CSV parsing, JSON batch import routes, live provider adapters, API polling, manual seed commands, or analysis execution.

## Purpose

All market data ingestion paths must converge into one internal object:

```txt
NormalizedCandleInput
```

Supported future origins:

- `csv_import`
- `json_import`
- `live_feed`
- `api_polling`
- `manual_seed`

The analysis engine should consume stored candles without caring which origin produced them.

## Modules

### `timeframes.py`

Defines supported timeframes:

- `1m`
- `5m`
- `15m`
- `30m`
- `1h`
- `4h`
- `1d`

It also provides UTC timestamp normalization and timestamp alignment checks.

### `schemas.py`

Defines:

- `NormalizedCandleInput`
- `CandleOriginType`
- `CandleValidationIssue`
- `CandleValidationResult`
- `CandleUpsertStatus`
- `CandleUpsertResult`
- `CandleRead`

`NormalizedCandleInput` includes:

- `workspace_id`
- `symbol_id`
- `source_id`
- `timeframe`
- `timestamp`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `is_final`
- `origin_type`
- `origin_reference_id`

The schema validates positive prices, non-negative volume, UTC timestamps, and OHLC relationships.

### `normalizer.py`

Converts a raw adapter payload into `NormalizedCandleInput`.

Adapters for CSV, JSON import, API polling, and live feed providers should call this module after parsing provider-specific input.

It handles:

- decimal conversion
- UTC timestamp normalization
- explicit origin metadata
- explicit final/partial state

### `validator.py`

Validates a normalized candle against repository objects:

- symbol exists and is active
- data source exists and is active
- timestamp aligns with timeframe
- candle origin matches data source type

Origin-to-source mapping:

```txt
csv_import -> csv_upload
json_import -> json_import
live_feed -> websocket_live
api_polling -> api_polling
manual_seed -> manual_seed
```

### `repository.py`

Owns storage and query behavior for `candles`.

Upsert behavior:

- If no candle exists, insert it.
- If an existing candle is partial and a new partial arrives, update the partial.
- If an existing candle is partial and a final candle arrives, replace partial values and mark final.
- If an existing candle is final and a later partial arrives, ignore it.
- If an existing candle is final and a matching final arrives, return `duplicate_final`.
- If an existing candle is final and a different final arrives, return `conflicting_final`.

The repository does not decide how to log or remediate conflicts. Future import/live workflows should use the returned status to write import errors or live feed processing failures.

### `quality.py`

Calculates candle window quality without performing database access.

Report fields:

- expected candle count
- available final candles
- available partial candles
- missing candles
- duplicate candles
- quality score
- latest partial candle flag

### `service.py`

Coordinates symbol lookup, source lookup, validation, and repository storage.

This service is internal for future ingestion workflows. It is not exposed through public candle routes in this slice.

## Final Vs Partial Policy

Final candles are the default source for analysis.

Partial live candles can exist in storage, but future analysis code must include them only when explicitly requested through a live analysis option.

## Conflict Policy

Conflicting final candles are not overwritten.

Future ingestion workflows should treat `conflicting_final` as an auditable data quality event. CSV imports should report it as an import error or duplicate conflict. Live feeds should mark the live event as failed or conflict depending on provider semantics.

## Not Implemented In This Slice

- CSV parser
- JSON import endpoint
- Live provider adapter
- API polling adapter
- Manual seed command
- Candle routes
- Import batch lifecycle
- Live feed event lifecycle
- Analysis run lifecycle
- Feature, indicator, pattern, signal, explanation, or news logic
