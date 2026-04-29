# Analysis Run Lifecycle

This document describes analysis orchestration and the deterministic artifact engines currently wired into it.

## Boundary

Implemented:

```txt
create historical analysis run
create live-window analysis run
resolve analysis window
resolve warmup and baseline windows
load candles through CandleService
calculate candle quality
write audit logs
transition run status
retry failed or insufficient-data runs
```

Not implemented:

```txt
signal classification
evidence generation
confidence scoring
risk notes
deterministic explanation
LLM explanation
news correlation
background worker execution
```

## API Endpoints

```txt
POST /analysis-runs
POST /analysis-runs/live-window
GET /analysis-runs
GET /analysis-runs/{analysis_run_id}
GET /analysis-runs/{analysis_run_id}/audit-logs
GET /analysis-runs/{analysis_run_id}/features
GET /analysis-runs/{analysis_run_id}/indicators
GET /analysis-runs/{analysis_run_id}/patterns
POST /analysis-runs/{analysis_run_id}/retry
```

## Historical Run

`POST /analysis-runs` creates a historical analysis run.

Required fields:

```txt
workspace_id
symbol_id
timeframe
start_time
end_time
```

Optional fields:

```txt
user_id
source_id
warmup_start_time
baseline_start_time
include_partial_live_candle
include_news_correlation
include_ai_explanation
```

The endpoint accepts only:

```txt
analysis_mode = historical
```

## Live-Window Run

`POST /analysis-runs/live-window` creates an analysis run from the latest stored candle.

Required fields:

```txt
workspace_id
symbol_id
timeframe
lookback_minutes
```

Optional fields:

```txt
user_id
source_id
warmup_candles
baseline_candles
include_partial_live_candle
include_news_correlation
include_ai_explanation
```

Default behavior:

```txt
latest final candle determines end_time
start_time = end_time - lookback_minutes
```

If `include_partial_live_candle=true`, latest final or partial candle may determine `end_time`.

## Status Transitions

This slice performs synchronous lifecycle preflight because background workers are not implemented yet.

Current transitions:

```txt
queued -> running -> completed
queued -> running -> insufficient_data
queued -> running -> failed
failed -> queued -> running -> completed
insufficient_data -> queued -> running -> completed
cancelled -> queued -> running -> completed
```

In this phase, `completed` means:

```txt
candle windows were loaded
quality was calculated
audit logs were written
feature snapshot was calculated and persisted
indicator snapshot was calculated and persisted
pattern candidates were calculated and persisted
deterministic signal classification was calculated and persisted
```

Future engine phases continue from stored artifacts into deterministic explanations, optional LLM explanations, and optional news correlation.

## Data Sufficiency Policy

A run is marked `insufficient_data` when:

```txt
analysis window has zero candles
expected candle count is zero
final candles are missing from the analysis window
```

Exception:

```txt
include_partial_live_candle=true
and exactly one final candle is missing
and the latest expected candle exists as partial
```

That exception supports live-window analysis that explicitly opts into the current partial candle.

## Audit Events

Current audit events:

```txt
analysis_created
analysis_running
candles_loaded
analysis_windows_resolved
features_calculated
indicators_calculated
patterns_detected
signal_classification_started
strategy_profiles_loaded
pattern_candidates_ranked
signal_selected
no_signal_generated
signal_classification_completed
signals_calculated
insufficient_data
analysis_completed
analysis_failed
analysis_retry_queued
```

Audit metadata stores window counts and data quality snapshots. It does not store secrets.

## Engine Version Fields

Until later intelligence engines exist, runs use:

```txt
engine_version = analysis_lifecycle_0.1.0
rule_set_version = preflight_0.1.0
```

These values identify analysis lifecycle plus feature, indicator, and pattern candidate runs and should change when broader deterministic engines are added.

## Retry Policy

`POST /analysis-runs/{analysis_run_id}/retry` accepts runs with status:

```txt
failed
insufficient_data
cancelled
```

Retry clears errors, queues the run, and performs lifecycle preflight again.

## Future Worker Boundary

When workers are added, they should reuse the service boundary:

```txt
AnalysisService.process_preflight
```

Workers should preserve audit logging and status transition semantics rather than writing analysis status directly.
