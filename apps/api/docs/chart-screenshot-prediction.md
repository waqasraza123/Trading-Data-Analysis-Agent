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
4. Optionally set `trigger_analysis=true` to run the existing deterministic analysis lifecycle over
   the extracted candle window.
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
POST /chart-screenshot-runs/image
GET /chart-screenshot-runs
GET /chart-screenshot-runs/{run_id}
GET /chart-screenshot-runs/{run_id}/decision
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
  "triggerAnalysis": true,
  "includeNewsCorrelation": false,
  "includeAiExplanation": false,
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
trigger_analysis=true
include_news_correlation=false
include_ai_explanation=false
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
- `analysisRunId`: populated when `triggerAnalysis` / `trigger_analysis` creates an analysis run.
- `extractionWarningsJson`: parser, validation, duplicate, and conflict warnings.
- `extractedPayloadJson`: submitted candles and trend metrics for audit/replay.
- `parserMetadataJson`: parser name/version, detected image size, chart bounds, detected candle
  count, image extraction warnings, and triggered analysis metadata when applicable.

The hypothesis is an evidence artifact for the backend and must not be presented as financial
advice or a guaranteed prediction.

## Analysis Triggering

Both create endpoints can trigger the normal deterministic analysis lifecycle after extracted
candles are committed.

Manual/external OHLC JSON uses camelCase fields:

```json
{
  "triggerAnalysis": true,
  "includeNewsCorrelation": false,
  "includeAiExplanation": false,
  "analysisWarmupStartTime": "2026-04-28T08:00:00Z",
  "analysisBaselineStartTime": "2026-04-28T12:00:00Z"
}
```

PNG multipart upload uses matching form fields:

```txt
trigger_analysis=true
include_news_correlation=false
include_ai_explanation=false
analysis_warmup_start_time=2026-04-28T08:00:00Z
analysis_baseline_start_time=2026-04-28T12:00:00Z
```

When analysis is triggered:

- the chart screenshot run stores the created `analysisRunId`;
- `status=analysis_triggered` means extraction completed and an analysis run was created;
- `parserMetadataJson.analysisTrigger.analysisStatus` records whether the created analysis run
  completed, failed, or returned `insufficient_data`;
- `status=analysis_failed` means extraction completed but the analysis run could not be created.

The analysis lifecycle still enforces normal candle sufficiency, final-candle reads, deterministic
feature/indicator/pattern/signal generation, deterministic explanation generation, and optional
news/LLM behavior.

## Decision Response

`GET /chart-screenshot-runs/{run_id}/decision` returns the client-facing next-direction decision
object for a chart screenshot run.

The endpoint prefers the linked deterministic analysis artifacts when they exist and the analysis
run completed. In that case:

- `decisionSource=deterministic_analysis`;
- `direction` comes from the persisted signal bias;
- `confidence` and `confidenceLabel` come from the persisted signal confidence;
- `reasoning` includes the signal summary, deterministic explanation sections, and persisted
  signal evidence messages;
- `signalClassification` contains the full signal, confidence components, evidence, risk notes,
  deterministic explanation, optional news correlations, and optional LLM explanation.

When no linked analysis run exists, or the linked analysis run is not completed, the endpoint falls
back to the lightweight screenshot trend hypothesis:

- `decisionSource=chart_screenshot_hypothesis`;
- `direction` and `confidence` come from the screenshot hypothesis stored on the run;
- `reasoning` includes stored candle counts and trend metrics from `extractedPayloadJson`;
- `warnings` explains why analysis-backed output was unavailable.

Example response shape:

```json
{
  "decisionSource": "deterministic_analysis",
  "direction": "bullish",
  "confidence": "0.7300",
  "confidenceLabel": "high",
  "reasoning": [
    "Bullish breakout passed profile thresholds.",
    "Evidence supports directional continuation with controlled risk notes."
  ],
  "warnings": [],
  "limitations": [
    "Chart screenshot outputs are hypotheses, not financial advice or trade instructions",
    "Image-derived candles depend on extraction quality and supplied calibration metadata"
  ],
  "analysisStatus": "completed",
  "analysisRun": {},
  "signalClassification": {},
  "chartScreenshotRun": {}
}
```

## Image Parser Limits

- Supported image format: non-interlaced 8-bit PNG, grayscale/RGB/RGBA.
- Supported chart type: visible candlestick shapes with foreground pixels that contrast from the
  chart background.
- Required calibration: `price_min`, `price_max`, `window_start`, and `timeframe`.
- The parser does not read axis text, infer symbol metadata from the image, or classify directly
  from pixels.
