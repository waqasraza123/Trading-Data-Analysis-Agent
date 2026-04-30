# Chart Screenshot Prediction

Chart screenshot prediction supports image-originated market analysis. The backend accepts either
manually or externally extracted OHLC candles, or a simple PNG candlestick chart with price/time
calibration metadata. In both paths, extracted candles are stored through the shared candle
validation/upsert path and a deterministic trend hypothesis is persisted for the next direction.

This slice does not perform OCR text reading, broker execution, or financial advice. The PNG parser
is deterministic and conservative: it detects candle geometry from visible colored candle pixels,
then refuses the request when at least three candle shapes cannot be found.
The expected production flow is:

1. Preview a supported chart PNG with `POST /chart-screenshot-runs/image/preview`, upload it to
   `POST /chart-screenshot-runs/image`, or submit reviewed OHLC
   rows to `POST /chart-screenshot-runs`.
2. Provide timeframe, start timestamp, and price range metadata for image extraction.
3. Review extracted candles, warnings, and the deterministic trend hypothesis before storage.
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
POST /chart-screenshot-runs/image/preview
POST /chart-screenshot-runs/image
GET /chart-screenshot-runs
GET /chart-screenshot-runs/{run_id}
POST /chart-screenshot-runs/{run_id}/review
GET /chart-screenshot-runs/{run_id}/decision
GET /chart-screenshot-runs/{run_id}/report
GET /chart-screenshot-runs/{run_id}/lineage
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

Optional parser tuning fields can be provided to both PNG endpoints:

```txt
foreground_distance_threshold=90
candle_color_delta_threshold=35
min_candle_channel=80
candle_blue_tolerance=20
active_column_min_pixels=2
column_gap_tolerance=3
min_cluster_width=2
body_row_coverage_percent=50
max_detected_candles=240
bullish_color_hex=#14a35c
bearish_color_hex=#d64b4b
color_profile_tolerance=80
```

Use these fields when exported charts have dark themes, muted candle colors, thick gridlines, or
platform-specific candle palettes. The parser stores the applied values in
`parserMetadataJson.parserTuning` so extraction can be audited and replayed.

## Preview PNG Image Extraction

`POST /chart-screenshot-runs/image/preview` runs deterministic PNG extraction without writing a
chart screenshot run, inserting candles, or triggering analysis. It is intended for UI review,
operator QA, and manual correction before persistence.

Submit the same image calibration fields used by the persisted PNG endpoint, except workspace,
source, and symbol identifiers are not required:

```txt
timeframe=15m
window_start=2026-04-29T08:00:00Z
price_min=63000
price_max=64000
file=@btc-chart.png
chart_left=48
chart_top=20
chart_right=900
chart_bottom=520
bullish_color_hex=#14a35c
bearish_color_hex=#d64b4b
```

Preview responses include:

- `candles`: extracted OHLC rows with timestamps and calibrated prices.
- `extractionConfidence`: deterministic extraction confidence from detected geometry.
- `analysisHypothesis`: lightweight trend hypothesis from the extracted closes.
- `analysisHypothesisConfidence`: hypothesis confidence after extraction confidence is applied.
- `trendMetricsJson`: first/last close, move ratio, directional step counts, and close consistency.
- `warnings`: extraction and hypothesis warnings.
- `requiresHumanReview`: `true` when confidence is below the production review threshold or warnings
  are present.
- `parserMetadataJson`: parser, image size, inferred/provided bounds, and detected candle count.

The preview endpoint is not an analysis endpoint. It does not persist artifacts and does not return
a trade decision. Persist the reviewed rows with `POST /chart-screenshot-runs` or persist the image
with `POST /chart-screenshot-runs/image`, then use the review and decision endpoints as needed.

## Parser Tuning

The default PNG parser is intentionally conservative and works best when candle pixels contrast
clearly from the chart background. Parser tuning is deterministic and request-scoped; it does not
change global service behavior.

Field semantics:

- `foreground_distance_threshold`: minimum RGB distance from the inferred background before a pixel
  is considered foreground. Lower values include more subtle pixels; higher values reject more
  gridlines and labels.
- `candle_color_delta_threshold`: minimum red/green channel difference for generic colored candle
  detection.
- `min_candle_channel`: minimum red or green channel value for generic colored candle detection.
- `candle_blue_tolerance`: allowed blue-channel slack relative to the dominant red/green channel.
- `active_column_min_pixels`: minimum foreground pixels required before an x-axis column can
  contribute to a candle cluster.
- `column_gap_tolerance`: maximum horizontal empty-pixel gap still treated as part of the same
  candle cluster.
- `min_cluster_width`: minimum width for a detected candle cluster.
- `body_row_coverage_percent`: percentage of candle-cluster width required for a row to be treated
  as candle body rather than wick.
- `max_detected_candles`: caps the number of extracted candles; when exceeded, the parser keeps the
  latest candles from the right side of the chart.
- `bullish_color_hex` / `bearish_color_hex`: optional exact candle colors for platforms that do not
  use a simple green/red palette.
- `color_profile_tolerance`: RGB distance tolerance for matching the optional bullish/bearish colors.

Recommended production workflow:

1. Call `/image/preview` with defaults.
2. If candles are missed, provide chart bounds and platform candle colors.
3. If gridlines or labels are included, increase `foreground_distance_threshold`,
   `active_column_min_pixels`, or `min_cluster_width`.
4. If candle bodies are split, increase `column_gap_tolerance`.
5. Persist the image only after preview output is acceptable, or submit corrected candles through
   the manual review path.

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
  count, parser tuning, image extraction warnings, and triggered analysis metadata when applicable.

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

## Human Review And Correction

`POST /chart-screenshot-runs/{run_id}/review` records human review metadata for a screenshot run.
This is the production safety path for low-confidence image extraction, platform-specific chart
styles, or cases where a user manually corrects extracted candles before relying on analysis.

Supported review statuses:

```txt
accepted
rejected
needs_correction
corrected
```

Accepted, rejected, and needs-correction reviews update `parserMetadataJson.humanReview` on the
original run. They do not mutate extracted candles and do not rewrite the original audit payload.
Accepted reviews may set `triggerAnalysis=true` to create an analysis run for the reviewed original
extraction. Rejected and needs-correction reviews cannot trigger analysis.

Corrected reviews require `correctedCandles`. The service creates a new chart screenshot run with:

- `parserName=human_review_correction`;
- `parserSourcePath=correction:{originalRunId}`;
- `extractionConfidence=1.0000`;
- `parserMetadataJson.correctedFromChartScreenshotRunId`;
- optional `triggerAnalysis`, news correlation, AI explanation, warmup, and baseline settings.

The original run is updated with `parserMetadataJson.humanReview.correctedChartScreenshotRunId`.
This preserves the original extraction and creates a separate auditable corrected run that flows
through the same candle validation, storage, hypothesis, and optional analysis lifecycle.

Example accepted review:

```json
{
  "reviewStatus": "accepted",
  "reviewerUserId": "00000000-0000-0000-0000-000000000000",
  "reviewNotes": "Candles match the uploaded chart closely enough for analysis.",
  "triggerAnalysis": true
}
```

Example corrected review:

```json
{
  "reviewStatus": "corrected",
  "reviewerUserId": "00000000-0000-0000-0000-000000000000",
  "reviewNotes": "Corrected the first candle high and final candle close.",
  "triggerAnalysis": true,
  "correctedCandles": [
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

## Audit Report

`GET /chart-screenshot-runs/{run_id}/report` returns a read-only audit bundle for a chart
screenshot run. It is intended for UI detail pages, support workflows, export pipelines, and
debugging extraction/analysis behavior without making multiple API calls.

The report includes:

- `chartScreenshotRun`: the persisted screenshot run.
- `storedCandles`: candles directly linked to the screenshot run through `chartScreenshotRunId`.
- `candleQuality`: quality report calculated over the extracted window from the directly linked
  candles.
- `decision`: the same response returned by `GET /chart-screenshot-runs/{run_id}/decision`.
- `reviewMetadataJson`: human review metadata when the run has been reviewed.
- `correctionRun`: the corrected chart screenshot run when a corrected review created one.
- `correctedFromRunId`: the original run when this report is for a human correction run.
- `trendMetricsJson`: persisted lightweight trend metrics from the extraction payload.
- `parserTuningJson`: parser tuning used for PNG extraction, when present.
- `auditWarnings`: extraction/storage warnings recorded on the run.
- `reportLimitations`: caveats that consumers should show or preserve in exports.

Important report semantics:

- `storedCandles` is intentionally limited to candles linked directly to the run; it does not fetch
  all candles in the same symbol/timeframe/window.
- Duplicate candles can be counted on `duplicateCount` without appearing in `storedCandles`, because
  duplicate storage reuses the existing candle row and does not rewrite its provenance.
- A corrected run is separate from the original run. Use `correctionRun` or `correctedFromRunId` to
  follow the review chain.
- The report is not a new analysis engine; it packages persisted backend artifacts for traceability.

Example response shape:

```json
{
  "chartScreenshotRun": {},
  "storedCandles": [],
  "candleQuality": {},
  "decision": {},
  "reviewMetadataJson": {},
  "correctionRun": null,
  "correctedFromRunId": null,
  "trendMetricsJson": {},
  "parserTuningJson": {},
  "auditWarnings": [],
  "reportLimitations": [
    "Report data is an audit bundle of persisted backend artifacts"
  ]
}
```

## Correction Lineage

`GET /chart-screenshot-runs/{run_id}/lineage` returns the correction chain for a chart screenshot
run. It is intended for UI navigation, support review, and safe handling of multiple corrections.

The lineage response includes:

- `requestedRun`: the run from the request path.
- `rootRun`: the earliest original run in the correction chain.
- `parentRun`: the immediate parent when the requested run is itself a correction.
- `correctionRuns`: all known correction runs below the root run, sorted by creation time.
- `latestCorrectionRun`: the newest correction run in the chain.
- `recommendedRun`: the latest correction run when one exists, otherwise the root run.
- `recommendedDecision`: the decision response for the recommended run.
- `lineageWarnings`: missing parent references, skipped loops, or other lineage integrity warnings.

Correction linkage is intentionally derived from persisted audit metadata:

- correction runs use `parserSourcePath=correction:{parentRunId}`;
- correction runs store `parserMetadataJson.correctedFromChartScreenshotRunId`;
- original runs store `parserMetadataJson.humanReview.correctedChartScreenshotRunId` when the
  review action created a correction.

Important semantics:

- The endpoint does not mutate runs or candles.
- It does not merge candles across runs. Use the report endpoint for run-specific candle audit data.
- When multiple correction generations exist, `recommendedRun` points to the latest correction by
  creation time.
- Lineage warnings should be preserved in UI/export flows because they indicate incomplete or
  inconsistent audit metadata.

Example response shape:

```json
{
  "requestedRun": {},
  "rootRun": {},
  "parentRun": null,
  "correctionRuns": [],
  "latestCorrectionRun": null,
  "recommendedRun": {},
  "recommendedDecision": {},
  "lineageWarnings": []
}
```

## Image Parser Limits

- Supported image format: non-interlaced 8-bit PNG, grayscale/RGB/RGBA.
- Supported chart type: visible candlestick shapes with foreground pixels that contrast from the
  chart background.
- Required calibration: `price_min`, `price_max`, `window_start`, and `timeframe`.
- Parser tuning can improve dark themes, muted colors, and gridline-heavy screenshots, but it does
  not replace review for low-confidence extraction.
- The parser does not read axis text, infer symbol metadata from the image, or classify directly
  from pixels.
