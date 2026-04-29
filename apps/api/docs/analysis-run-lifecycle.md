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
replay completed runs from stored candles with latest deterministic engine version
replay completed runs from stored candles with same registered deterministic engine version
```

Not implemented:

```txt
LLM explanation
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
POST /analysis-runs/{analysis_run_id}/correlate-news
GET /analysis-runs/{analysis_run_id}/news-correlations
POST /analysis-runs/{analysis_run_id}/retry
POST /analysis-runs/{analysis_run_id}/replay
GET /analysis-runs/{analysis_run_id}/replays
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
completed -> replay queued -> running -> completed
```

## Replay

`POST /analysis-runs/{analysis_run_id}/replay` creates a new analysis run with:

```txt
analysis_mode = replay
replayed_from_analysis_run_id = original run id
replay_mode = latest_engine_version
engine_snapshot_json = active engine version snapshot
rule_set_snapshot_json = active rule/profile snapshot
```

Replay copies the original workspace, user, symbol, source, timeframe, analysis window,
warmup window, baseline window, and partial-candle setting. It then reuses the same
synchronous lifecycle over stored candles and persists new feature, indicator, pattern,
signal, confidence, evidence, risk, and deterministic explanation artifacts for the
replay run.

`latest_engine_version` re-runs with the currently registered deterministic engine versions
and active strategy profiles.

`same_engine_version` re-runs with the original run's stored engine snapshot and rule-set
snapshot when those versions are registered in this codebase. It reuses the original signal's
strategy profile snapshot for classification when one exists. If a snapshot references an
unregistered version, replay returns `unsupported_engine_version` and does not silently fall
back to latest behavior.

Replay does not mutate the original run or its artifacts. Each request creates a new linked
replay run.

In this phase, `completed` means:

```txt
candle windows were loaded
quality was calculated
audit logs were written
feature snapshot was calculated and persisted
indicator snapshot was calculated and persisted
pattern candidates were calculated and persisted
deterministic signal classification was calculated and persisted
optional deterministic news correlations were calculated when requested
deterministic explanation was generated and persisted
```

Future engine phases continue from stored artifacts into optional LLM explanations, scanners,
and external provider integrations.

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
analysis_replay_requested
analysis_replay_created
analysis_replay_started
analysis_replay_completed
analysis_replay_failed
analysis_replay_unsupported_engine_version
deterministic_explanation_started
deterministic_explanation_generated
deterministic_explanation_blocked
deterministic_explanation_failed
deterministic_explanations_calculated
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
