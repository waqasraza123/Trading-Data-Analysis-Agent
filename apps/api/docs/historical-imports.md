# Historical Candle Import Pipeline

This slice wires historical CSV and JSON candle imports into the backend. It does not add live feed providers, scheduled scans, analysis execution, indicators, patterns, signals, news correlation, LLM explanations, or UI behavior.

## Endpoints

```txt
POST /imports/candles/csv
POST /imports/candles/json
GET /imports/{import_batch_id}
GET /imports/{import_batch_id}/errors
```

## Shared Storage Path

Both CSV and JSON imports use the same flow:

```txt
request
→ import batch
→ parse rows
→ RawCandlePayload
→ NormalizedCandleInput
→ candle validator
→ candle repository upsert
→ import counters/errors
→ import batch final status
```

Import code must not write directly to the `candles` table.

## CSV Import

CSV upload expects multipart form data:

```txt
workspace_id
source_id
symbol_id
timeframe
user_id optional
file
```

Required CSV columns:

```txt
timestamp
open
high
low
close
```

Optional CSV columns:

```txt
volume
```

CSV files must be UTF-8 encoded. UTF-8 with BOM is accepted.

## JSON Import

JSON import expects a structured request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "userId": null,
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "timeframe": "1m",
  "candles": [
    {
      "timestamp": "2026-04-29T09:00:00Z",
      "open": "1.08420",
      "high": "1.08450",
      "low": "1.08410",
      "close": "1.08440",
      "volume": "1200"
    }
  ]
}
```

## Batch Status Rules

Final status is calculated after row processing:

- `completed`: at least one valid candle, no invalid rows, no duplicates, no missing candles.
- `completed_with_warnings`: at least one valid candle plus invalid rows, duplicates, or missing candles.
- `failed`: no valid candles were stored.

## Duplicate And Conflict Rules

Historical imports use the shared candle repository:

- Matching duplicate final candles are skipped and counted as duplicates.
- Late partial candles are ignored if a final candle already exists.
- Conflicting final candles are not overwritten and become row-level import errors.
- Partial-to-final replacement is supported by the shared candle repository, though CSV/JSON imports currently submit final candles only.

## Import Errors

Row-level failures are stored in `import_errors`.

Common error codes:

- `missing_required_column`
- `invalid_row`
- `invalid_timestamp`
- `invalid_timeframe`
- `invalid_open`
- `invalid_high`
- `invalid_low`
- `invalid_close`
- `invalid_volume`
- `invalid_ohlc_relationship`
- `inactive_symbol`
- `inactive_source`
- `origin_reference_mismatch`
- `conflicting_final_candle`

## Quality Score

The import service calculates a bounded `data_quality_score` from:

- valid rows
- invalid rows
- duplicates skipped
- missing candle count

The score is stored on `import_batches` for audit and future UI display.

## Workspace And Source Boundary

The requested `source_id` must belong to the requested `workspace_id`.

CSV imports must use a `csv_upload` data source.

JSON imports must use a `json_import` data source.

Inactive symbols and inactive/failed data sources are rejected at row validation time and persisted as import errors.

## Not Implemented In This Slice

- Background import workers
- File object storage
- Import retry endpoint
- Candle query routes
- Live feed ingestion
- Analysis run creation
- Feature, indicator, pattern, signal, explanation, or news logic
