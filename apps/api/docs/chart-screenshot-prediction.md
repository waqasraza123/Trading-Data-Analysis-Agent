# Chart Screenshot Prediction

Chart screenshot prediction is the first backend slice for image-originated market analysis.
This implementation accepts manually or externally extracted OHLC candles from a chart image,
stores them through the shared candle validation/upsert path, and persists a deterministic trend
hypothesis for the next direction.

This slice does not perform OCR, image geometry detection, broker execution, or financial advice.
The expected production flow is:

1. Upload or inspect a chart image outside this endpoint.
2. Extract candle-like OHLC rows with a bounded parser or manual review.
3. Submit those rows to `POST /chart-screenshot-runs`.
4. Review stored counts, warnings, and the deterministic trend hypothesis.
5. Use the persisted candle rows with existing candle/query/analysis APIs as needed.

## Data Source

Screenshot-derived candles require a data source with:

```txt
source_type=chart_screenshot
provider=manual_ocr
```

The seed command creates a default `chart_screenshot` data source when a default workspace is
configured.

## Endpoints

```txt
POST /chart-screenshot-runs
GET /chart-screenshot-runs
GET /chart-screenshot-runs/{run_id}
```

## Create Request

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "sourceId": "00000000-0000-0000-0000-000000000000",
  "symbolId": "00000000-0000-0000-0000-000000000000",
  "timeframe": "15m",
  "fileName": "btc-chart.png",
  "parserSourcePath": "manual-review",
  "extractionConfidence": "0.8500",
  "parserMetadataJson": {
    "imageTimeZone": "UTC",
    "chartPlatform": "manual"
  },
  "candles": [
    {
      "timestamp": "2026-04-29T08:00:00Z",
      "open": "63000",
      "high": "63300",
      "low": "62800",
      "close": "63250",
      "volume": "120"
    },
    {
      "timestamp": "2026-04-29T08:15:00Z",
      "open": "63250",
      "high": "63600",
      "low": "63100",
      "close": "63520",
      "volume": "140"
    },
    {
      "timestamp": "2026-04-29T08:30:00Z",
      "open": "63520",
      "high": "63750",
      "low": "63400",
      "close": "63700",
      "volume": "132"
    }
  ]
}
```

## Response Semantics

The response persists:

- `status`: `completed` when extracted candles were stored or already existed, `failed` when none
  could be stored or matched.
- `storedCandleCount`, `duplicateCount`, `conflictCount`: shared candle upsert outcomes.
- `analysisHypothesis`: deterministic `bullish`, `bearish`, `neutral`, or `unclear` label.
- `analysisHypothesisConfidence`: confidence from close-direction consistency, move magnitude, and
  extraction confidence.
- `extractionWarningsJson`: parser, validation, duplicate, and conflict warnings.
- `extractedPayloadJson`: submitted candles and trend metrics for audit/replay.

The hypothesis is an evidence artifact for the backend and must not be presented as financial
advice or a guaranteed prediction.
