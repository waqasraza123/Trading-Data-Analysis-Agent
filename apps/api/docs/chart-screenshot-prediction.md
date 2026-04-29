# Chart Screenshot Prediction

Chart screenshot prediction supports image-originated market analysis. The backend accepts either
manually or externally extracted OHLC candles, or a simple PNG candlestick chart with price/time
calibration metadata. In both paths, extracted candles are stored through the shared candle
validation/upsert path and a deterministic trend hypothesis is persisted for the next direction.

This slice does not perform OCR text reading, broker execution, or financial advice. The PNG parser
is deterministic and conservative: it detects candle geometry from visible colored candle pixels,
then refuses the request when at least three candle shapes cannot be found.
The expected production flow is:

1. Upload a supported chart PNG to `POST /chart-screenshot-runs/image`, or submit reviewed OHLC
   rows to `POST /chart-screenshot-runs`.
2. Provide symbol, source, timeframe, start timestamp, and price range metadata.
3. Review stored counts, warnings, and the deterministic trend hypothesis.
4. Use the persisted candle rows with existing candle/query/analysis APIs as needed.

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
POST /chart-screenshot-runs/image
GET /chart-screenshot-runs
GET /chart-screenshot-runs/{run_id}
```

## Create Request With Extracted Candles

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

## Create Request With PNG Image

Submit `multipart/form-data` to `POST /chart-screenshot-runs/image`:

```txt
workspace_id=00000000-0000-0000-0000-000000000000
source_id=00000000-0000-0000-0000-000000000000
symbol_id=00000000-0000-0000-0000-000000000000
timeframe=15m
window_start=2026-04-29T08:00:00Z
price_min=63000
price_max=64000
file=@btc-chart.png
```

Optional chart bounds can be provided when the chart contains legends, toolbars, or other
non-chart pixels:

```txt
chart_left=48
chart_top=20
chart_right=900
chart_bottom=520
```

If bounds are omitted, the parser infers them from foreground pixels and records a warning in
`parserMetadataJson.imageExtractionWarnings`.

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
- `parserMetadataJson`: parser name/version, detected image size, chart bounds, detected candle
  count, and image extraction warnings when applicable.

The hypothesis is an evidence artifact for the backend and must not be presented as financial
advice or a guaranteed prediction.

## Image Parser Limits

- Supported image format: non-interlaced 8-bit PNG, grayscale/RGB/RGBA.
- Supported chart type: visible candlestick shapes with foreground pixels that contrast from the
  chart background.
- Required calibration: `price_min`, `price_max`, `window_start`, and `timeframe`.
- The parser does not read axis text, infer symbol metadata from the image, or classify directly
  from pixels.
