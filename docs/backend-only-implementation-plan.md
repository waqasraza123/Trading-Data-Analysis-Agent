# Backend-Only Implementation Plan

# AI Trading Intelligence Agent

## FastAPI + Neon PostgreSQL

This plan focuses only on the **main intelligence backend layer**. No UI, no frontend, no visual dashboard yet.

The goal is to build a production-grade backend that can:

```txt
ingest market data
validate candles
store clean time-series data
calculate market features
calculate indicators
detect patterns
classify market behavior
generate evidence-backed signals
correlate movements with news/events
generate safe AI explanations
store every output for audit/replay
expose clean APIs for the UI later
```

The core rule:

> **Neon stores the truth. FastAPI controls the workflow. Deterministic engines calculate and classify. AI only explains.**

---

# 1. Backend Product Boundary

This backend is not a chatbot.

It is a **market intelligence engine**.

It should accept structured market data and return structured analysis.

## The backend should do

```txt
Parse OHLC candle data
Validate and normalize candles
Store candles in Neon
Calculate pip/tick movement
Calculate candle body/wick metrics
Calculate range behavior
Calculate volatility behavior
Calculate indicators
Detect bullish/bearish/neutral patterns
Classify signal bias
Generate confidence score
Generate evidence
Generate risk notes
Optionally correlate with news/events
Optionally generate LLM explanation
Store all artifacts
Expose APIs for future UI
```

## The backend should not do yet

```txt
Frontend UI
Chart rendering
Broker trading
Auto-execution
Copy trading
Social trading
Financial advice
Guaranteed trade signals
```

The backend output should always be:

```txt
analysis, evidence, confidence, explanation
```

Not:

```txt
buy now, sell now, guaranteed profit
```

---

# 2. Recommended Backend Stack

## Core stack

```txt
FastAPI
Python 3.12+
Pydantic v2
SQLAlchemy 2.x async
Alembic migrations
Neon PostgreSQL
asyncpg
Redis
Celery / RQ / Dramatiq for background jobs
Polars or Pandas for candle calculations
NumPy for numeric operations
OpenAI/Anthropic only for explanation layer
Pytest for tests
Ruff for linting
Mypy or Pyright for typing
```

## Database

Use:

```txt
Neon PostgreSQL
```

Neon will be the main source of truth for:

```txt
symbols
candles
imports
analysis runs
feature snapshots
indicator snapshots
pattern candidates
signals
evidence
confidence components
news events
LLM explanations
engine versions
audit logs
```

Important note:

For early and medium scale, Neon PostgreSQL is enough.

For very heavy historical tick/minute data later, consider a separate analytical store such as ClickHouse, but do **not** add it in the first version unless needed.

Start clean with Neon.

---

# 3. High-Level Backend Architecture

```txt
FastAPI API Layer
        ↓
Service Layer
        ↓
Job Queue
        ↓
Analysis Worker
        ↓
Candle Repository / Neon
        ↓
Feature Engineering Engine
        ↓
Indicator Engine
        ↓
Pattern Detection Engine
        ↓
Signal Classification Engine
        ↓
Evidence + Confidence Engine
        ↓
News/Event Correlation Engine
        ↓
Deterministic Explanation Engine
        ↓
Optional LLM Explanation Engine
        ↓
Persisted Analysis Artifacts
```

The important design decision:

> Every major step should persist output into Neon, so the system is auditable and replayable.

---

# 4. Backend Folder Structure

Recommended structure:

```txt
apps/api/
  app/
    main.py
    config.py
    dependencies.py

    db/
      session.py
      base.py
      migrations/
      repositories/

    core/
      errors.py
      logging.py
      security.py
      pagination.py
      idempotency.py
      time.py

    modules/
      symbols/
        models.py
        schemas.py
        repository.py
        service.py
        routes.py

      imports/
        models.py
        schemas.py
        parser.py
        validator.py
        service.py
        jobs.py
        routes.py

      candles/
        models.py
        schemas.py
        repository.py
        quality.py
        service.py
        routes.py

      analysis/
        models.py
        schemas.py
        lifecycle.py
        service.py
        jobs.py
        routes.py

      features/
        schemas.py
        engine.py
        movement.py
        candle_shape.py
        volatility.py
        trend.py
        range.py

      indicators/
        engine.py
        ema.py
        rsi.py
        macd.py
        atr.py
        schemas.py

      patterns/
        engine.py
        schemas.py
        bullish_breakout.py
        bearish_breakdown.py
        continuation.py
        reversal.py
        fakeout.py
        chop.py

      signals/
        models.py
        schemas.py
        classifier.py
        confidence.py
        evidence.py
        risk_notes.py
        repository.py

      news/
        models.py
        schemas.py
        ingestion.py
        correlation.py
        service.py
        routes.py

      explanations/
        models.py
        deterministic.py
        llm.py
        prompts.py
        safety.py
        service.py

      engine_versions/
        models.py
        service.py

      audit/
        models.py
        service.py

    workers/
      celery_app.py
      import_worker.py
      analysis_worker.py
      explanation_worker.py
      news_worker.py

    tests/
      unit/
      integration/
      golden/
```

Keep engines separated from API routes.

Routes should not contain business logic.

---

# 5. Database Design in Neon

## 5.1 Core principle

Neon should store:

```txt
raw input metadata
clean normalized candles
every analysis run
every calculated snapshot
every detected pattern candidate
final signal
all evidence
all confidence components
all AI explanations
engine version used
```

This gives production-grade auditability.

---

# 6. Database Tables

## 6.1 `workspaces`

Even if the first version has one user, add workspaces early.

```txt
id
name
created_at
updated_at
```

Why?

Later this supports:

```txt
teams
educators
trading groups
white-label clients
billing
data isolation
```

---

## 6.2 `users`

```txt
id
workspace_id
email
name
role
created_at
updated_at
```

Roles:

```txt
admin
user
analyst
```

---

## 6.3 `symbols`

Stores market instruments.

```txt
id
symbol
display_name
market_type
base_asset
quote_asset
pip_size
tick_size
price_precision
quantity_precision
is_active
created_at
updated_at
```

Examples:

```txt
EURUSD
market_type: forex
pip_size: 0.0001
```

```txt
USDJPY
market_type: forex
pip_size: 0.01
```

```txt
BTCUSDT
market_type: crypto
tick_size: 0.01
```

This table is critical because pip calculations depend on symbol metadata.

---

## 6.4 `data_sources`

```txt
id
workspace_id
name
source_type
provider
status
config_json
created_at
updated_at
```

Source types:

```txt
csv_upload
api_import
websocket
manual_seed
```

For MVP:

```txt
csv_upload
```

---

## 6.5 `import_batches`

Tracks every import.

```txt
id
workspace_id
user_id
source_id
symbol_id
timeframe
file_name
file_url
status
rows_received
rows_valid
rows_invalid
duplicates_skipped
missing_candles_detected
data_quality_score
error_summary_json
started_at
completed_at
created_at
updated_at
```

Statuses:

```txt
pending
processing
completed
completed_with_warnings
failed
cancelled
```

---

## 6.6 `import_errors`

Stores row-level import errors.

```txt
id
import_batch_id
row_number
error_code
error_message
raw_row_json
created_at
```

Error codes:

```txt
invalid_timestamp
invalid_open
invalid_high
invalid_low
invalid_close
invalid_ohlc_relationship
duplicate_timestamp
unsupported_timeframe
missing_required_column
```

---

## 6.7 `candles`

The core time-series table.

```txt
id
workspace_id
symbol_id
source_id
import_batch_id
timeframe
timestamp
open
high
low
close
volume
created_at
```

Recommended numeric types:

```txt
open numeric(24, 10)
high numeric(24, 10)
low numeric(24, 10)
close numeric(24, 10)
volume numeric(30, 10)
```

Important indexes:

```txt
workspace_id, symbol_id, timeframe, timestamp
symbol_id, timeframe, timestamp
import_batch_id
timestamp
```

Unique constraint:

```txt
workspace_id + symbol_id + source_id + timeframe + timestamp
```

For large scale later, consider monthly partitioning by timestamp.

But do not overcomplicate MVP unless candle volume is already huge.

---

## 6.8 `analysis_runs`

Each request to analyze market data creates one analysis run.

```txt
id
workspace_id
user_id
symbol_id
timeframe
start_time
end_time
warmup_start_time
baseline_start_time
include_news_correlation
include_ai_explanation
status
error_code
error_message
engine_version
rule_set_version
started_at
completed_at
created_at
updated_at
```

Statuses:

```txt
queued
running
completed
failed
insufficient_data
cancelled
```

This table is the backbone of the backend workflow.

---

## 6.9 `feature_snapshots`

Stores calculated feature output.

```txt
id
analysis_run_id
workspace_id
symbol_id
timeframe
start_time
end_time
features_json
created_at
```

Example `features_json`:

```json
{
  "movement": {
    "startPrice": "1.08420",
    "endPrice": "1.08604",
    "absoluteMove": "0.00184",
    "pipsMoved": 18.4,
    "direction": "bullish",
    "movementEfficiency": 0.62
  },
  "range": {
    "previousRangeHigh": "1.08540",
    "previousRangeLow": "1.08310",
    "candlesClosedAboveRange": 3,
    "candlesClosedBelowRange": 0
  },
  "volatility": {
    "atr": "0.00032",
    "baselineAtr": "0.00019",
    "atrExpansionRatio": 1.68,
    "state": "expanding"
  },
  "trend": {
    "higherHighsCount": 5,
    "higherLowsCount": 6,
    "lowerHighsCount": 1,
    "lowerLowsCount": 0,
    "state": "short_term_uptrend"
  }
}
```

Why JSON?

Because feature shape may evolve. Keep structured snapshots flexible while core signal fields remain normalized.

---

## 6.10 `indicator_snapshots`

Stores indicator values separately.

```txt
id
analysis_run_id
workspace_id
symbol_id
timeframe
indicators_json
created_at
```

Example:

```json
{
  "ema": {
    "ema9": "1.08570",
    "ema21": "1.08510",
    "ema50": "1.08440",
    "alignment": "bullish"
  },
  "rsi": {
    "period": 14,
    "value": 64.2,
    "state": "bullish_momentum"
  },
  "macd": {
    "macd": 0.00016,
    "signal": 0.00008,
    "histogram": 0.00008,
    "state": "bullish"
  },
  "atr": {
    "period": 14,
    "value": "0.00032",
    "state": "expanding"
  }
}
```

---

## 6.11 `pattern_candidates`

Stores every pattern the engine considered.

```txt
id
analysis_run_id
workspace_id
symbol_id
pattern_type
bias
strength_score
is_selected
evidence_json
risk_notes_json
metrics_json
created_at
```

This is important.

Do not only store the final signal. Store candidates too.

Example:

```txt
bullish_breakout strength 0.78 selected true
fakeout strength 0.22 selected false
sideways_range strength 0.16 selected false
```

This helps debugging and improves trust.

---

## 6.12 `signals`

Final classified signal.

```txt
id
analysis_run_id
workspace_id
symbol_id
timeframe
bias
pattern_type
confidence_score
confidence_label
pips_moved
movement_direction
movement_quality
volatility_state
trend_state
range_state
invalidation_level
summary
created_at
```

Bias:

```txt
bullish
bearish
neutral
unclear
```

Confidence label:

```txt
low
medium
high
very_high
```

Movement quality:

```txt
clean
moderate
choppy
volatile
unclear
```

---

## 6.13 `signal_evidence`

Every signal must explain itself.

```txt
id
signal_id
evidence_type
direction
message
numeric_value
weight
metadata_json
created_at
```

Evidence types:

```txt
price_action
range_break
trend_structure
volatility
indicator
data_quality
news_event
risk_warning
```

Direction:

```txt
supports_bullish
supports_bearish
supports_neutral
risk_warning
contradicts_signal
```

Example:

```txt
Evidence type: range_break
Direction: supports_bullish
Message: Price closed above the previous 60-minute range high for 3 candles.
Weight: 0.25
```

---

## 6.14 `signal_confidence_components`

Confidence must be explainable.

```txt
id
signal_id
component_name
component_score
component_weight
weighted_score
reason
created_at
```

Components:

```txt
pattern_strength
trend_alignment
volatility_confirmation
indicator_support
data_quality
news_context
```

Example:

```txt
pattern_strength: 0.82 weight 0.30
trend_alignment: 0.76 weight 0.20
volatility_confirmation: 0.71 weight 0.20
indicator_support: 0.64 weight 0.15
data_quality: 0.95 weight 0.10
news_context: 0.00 weight 0.05
```

This makes confidence transparent.

---

## 6.15 `news_events`

For later phase.

```txt
id
workspace_id
source
title
description
event_time
currency
asset
importance
actual_value
forecast_value
previous_value
sentiment
url
raw_payload_json
created_at
```

Importance:

```txt
low
medium
high
critical
```

---

## 6.16 `signal_news_correlations`

```txt
id
signal_id
news_event_id
time_delta_minutes
correlation_score
correlation_label
reason
created_at
```

Labels:

```txt
none
weak
possible
strong
```

---

## 6.17 `deterministic_explanations`

Non-LLM summaries.

```txt
id
signal_id
summary_text
template_version
created_at
```

Always generate this.

---

## 6.18 `llm_explanations`

Optional AI explanation.

```txt
id
signal_id
provider
model
prompt_version
input_json
output_text
safety_status
tokens_input
tokens_output
estimated_cost
created_at
```

Safety statuses:

```txt
passed
blocked
fallback_used
requires_review
```

---

## 6.19 `engine_versions`

Version every engine.

```txt
id
engine_name
version
description
config_json
created_at
```

Engine names:

```txt
feature_engine
indicator_engine
pattern_engine
signal_classifier
confidence_engine
news_correlation_engine
llm_explanation_engine
```

Why?

Because later, if signal logic changes, old outputs remain traceable.

---

## 6.20 `analysis_audit_logs`

```txt
id
analysis_run_id
event_type
message
metadata_json
created_at
```

Events:

```txt
analysis_created
candles_loaded
insufficient_data
features_calculated
indicators_calculated
patterns_detected
signal_classified
explanation_generated
analysis_failed
analysis_completed
```

---

# 7. Backend API Plan

Even without UI, define APIs cleanly.

## 7.1 Health

```txt
GET /health
GET /health/db
GET /health/worker
```

Returns:

```json
{
  "status": "healthy",
  "database": "healthy",
  "worker": "healthy"
}
```

---

## 7.2 Symbols

```txt
POST /symbols
GET /symbols
GET /symbols/{symbol_id}
PATCH /symbols/{symbol_id}
```

Purpose:

Manage symbol metadata for pip/tick calculations.

---

## 7.3 Imports

```txt
POST /imports/candles
GET /imports/{import_batch_id}
GET /imports/{import_batch_id}/errors
```

Upload or register candle data.

For backend testing, support both:

```txt
CSV upload
JSON candle batch
```

JSON batch is useful for automated tests and integrations.

---

## 7.4 Candles

```txt
GET /candles
GET /candles/quality
GET /candles/count
```

Query params:

```txt
symbol_id
timeframe
start_time
end_time
source_id
```

---

## 7.5 Analysis Runs

```txt
POST /analysis-runs
GET /analysis-runs/{analysis_run_id}
GET /analysis-runs
POST /analysis-runs/{analysis_run_id}/retry
```

Create request:

```json
{
  "symbolId": "sym_123",
  "timeframe": "1m",
  "startTime": "2026-04-29T09:00:00Z",
  "endTime": "2026-04-29T10:00:00Z",
  "includeNewsCorrelation": false,
  "includeAiExplanation": true
}
```

Response:

```json
{
  "analysisRunId": "run_123",
  "status": "queued"
}
```

---

## 7.6 Signals

```txt
GET /signals/{signal_id}
GET /signals
GET /signals/{signal_id}/evidence
GET /signals/{signal_id}/confidence
```

This will power the UI later.

---

## 7.7 Engine Diagnostics

Internal/admin APIs:

```txt
GET /analysis-runs/{id}/features
GET /analysis-runs/{id}/indicators
GET /analysis-runs/{id}/patterns
GET /analysis-runs/{id}/audit-logs
```

These are critical for production debugging.

---

# 8. Core Backend Pipeline

The analysis pipeline should be deterministic and step-based.

## Full pipeline

```txt
1. Create analysis run
2. Resolve symbol metadata
3. Resolve analysis window
4. Resolve warmup/baseline windows
5. Load candles from Neon
6. Run data quality checks
7. If insufficient data, stop cleanly
8. Calculate movement features
9. Calculate candle shape features
10. Calculate range features
11. Calculate volatility features
12. Calculate trend features
13. Calculate indicators
14. Detect pattern candidates
15. Select strongest pattern
16. Classify final signal
17. Generate evidence
18. Generate confidence components
19. Generate risk notes
20. Optional: correlate news/events
21. Generate deterministic explanation
22. Optional: generate LLM explanation
23. Persist all outputs
24. Mark analysis completed
```

Every step should be logged in `analysis_audit_logs`.

---

# 9. Phase-by-Phase Backend Implementation

# Phase 1: FastAPI + Neon Foundation

## Goal

Set up the backend correctly before adding intelligence.

## Tasks

```txt
Create FastAPI app
Set up Pydantic settings
Set up async SQLAlchemy
Connect to Neon using asyncpg
Set up Alembic migrations
Add structured logging
Add app-level exception handling
Add health endpoints
Add pytest
Add Ruff
Add type checking
Add Dockerfile
Add CI pipeline
```

## Done criteria

```txt
FastAPI starts successfully
Neon connection works
Migrations run successfully
Health endpoint works
Tests run in CI
Errors return clean JSON
Logs are structured
```

---

# Phase 2: Symbol Configuration Engine

## Goal

Create symbol metadata because calculations depend on it.

## Tasks

```txt
Create symbols table
Create symbol schemas
Create symbol repository
Create symbol service
Seed common symbols
Add pip_size/tick_size validation
Add active/inactive status
```

## Seed examples

```txt
EURUSD pip_size 0.0001
GBPUSD pip_size 0.0001
USDJPY pip_size 0.01
XAUUSD pip_size configurable
BTCUSDT tick_size 0.01
ETHUSDT tick_size 0.01
```

## Done criteria

```txt
Symbol metadata can be created
Pip size is required for forex
Tick size is required for crypto
Inactive symbols cannot be analyzed
Symbol metadata is accessible by analysis engine
```

---

# Phase 3: Candle Import Backend

## Goal

Build ingestion without analysis first.

## Tasks

```txt
Create data_sources table
Create import_batches table
Create import_errors table
Create candles table
Build CSV parser
Build JSON batch parser
Validate rows
Normalize timestamps to UTC
Validate OHLC structure
Skip duplicates
Store valid candles
Store invalid row errors
Calculate data quality score
```

## Candle validation rules

```txt
timestamp exists
timestamp valid
timestamp aligns with timeframe
open/high/low/close numeric
high >= open
high >= close
high >= low
low <= open
low <= close
volume numeric if present
no negative price
symbol exists
timeframe supported
```

## Done criteria

```txt
Valid CSV imports candles
Invalid CSV produces import errors
Duplicate timestamps are skipped or reported
Import summary is accurate
Candles are stored in Neon
No analysis logic exists yet
```

---

# Phase 4: Candle Query and Quality Layer

## Goal

Create a reliable read layer for analysis.

## Tasks

```txt
Build candle repository
Fetch candles by symbol/timeframe/window
Fetch warmup candles
Fetch baseline candles
Detect missing timestamps
Count candles in window
Calculate data completeness
Return clean ordered candle series
```

## Data quality output

```json
{
  "expectedCandles": 60,
  "availableCandles": 58,
  "missingCandles": 2,
  "duplicateCandles": 0,
  "qualityScore": 0.966
}
```

## Done criteria

```txt
Analysis engine can request candle windows cleanly
Missing candle detection works
Warmup window retrieval works
Baseline window retrieval works
Insufficient data is detected before calculations
```

---

# Phase 5: Analysis Run Lifecycle

## Goal

Create production-grade analysis orchestration.

## Tasks

```txt
Create analysis_runs table
Create analysis service
Create analysis job
Add queue worker
Add run status transitions
Add retry support
Add audit logging
Add failure handling
```

## State transition

```txt
queued → running → completed
queued → running → insufficient_data
queued → running → failed
failed → queued on retry
```

## Done criteria

```txt
Analysis run can be created
Worker picks it up
Status updates correctly
Failures are stored
Audit logs are written
Retry works safely
```

---

# Phase 6: Feature Engineering Engine

## Goal

Build the first intelligence layer.

## Engine input

```txt
symbol metadata
analysis candles
warmup candles
baseline candles
```

## Engine output

```txt
feature snapshot
```

## Feature groups

### Movement features

```txt
start_price
end_price
absolute_move
percentage_move
pips_moved
tick_moved
net_direction
total_movement
movement_efficiency
```

### Candle shape features

```txt
average_body_size
average_upper_wick
average_lower_wick
body_to_range_ratio
large_body_count
large_wick_count
indecision_count
rejection_count
```

### Range features

```txt
previous_range_high
previous_range_low
current_range_high
current_range_low
candles_closed_above_previous_range
candles_closed_below_previous_range
distance_from_range_high
distance_from_range_low
```

### Volatility features

```txt
true_range
current_average_range
baseline_average_range
atr
baseline_atr
atr_expansion_ratio
volatility_state
large_candle_count
```

### Trend features

```txt
higher_highs_count
higher_lows_count
lower_highs_count
lower_lows_count
trend_slope
trend_state
```

## Done criteria

```txt
Feature engine produces deterministic output
Feature snapshot is stored
Pip calculation works for EURUSD
JPY pip calculation works
Crypto tick calculation works
Unit tests cover all feature groups
```

---

# Phase 7: Indicator Engine

## Goal

Calculate standard indicators as supporting evidence.

## MVP indicators

```txt
EMA 9
EMA 21
EMA 50
RSI 14
MACD
ATR 14
```

## Indicator states

EMA:

```txt
bullish_alignment
bearish_alignment
mixed
```

RSI:

```txt
oversold
bearish_momentum
neutral
bullish_momentum
overbought
```

MACD:

```txt
bullish
bearish
neutral
```

ATR:

```txt
compressed
normal
expanding
spike
```

## Done criteria

```txt
Indicators calculate from warmup candles
Indicator snapshot is stored
Indicators are deterministic
Indicator tests pass on known data
Missing warmup data returns clear insufficient-data error
```

---

# Phase 8: Pattern Detection Engine

## Goal

Detect candidate market patterns.

Start rule-based. Do not use ML first.

## Pattern candidate output

```json
{
  "patternType": "bullish_breakout",
  "bias": "bullish",
  "strengthScore": 0.78,
  "evidence": [],
  "riskNotes": [],
  "metrics": {}
}
```

## Required detectors

### 8.1 Bullish Breakout

Conditions:

```txt
price closes above previous range high
at least N candles hold above range high
ATR normal or expanding
recent structure shows higher lows
breakout candle has acceptable body strength
```

Output:

```txt
bias bullish
pattern bullish_breakout
```

---

### 8.2 Bearish Breakdown

Conditions:

```txt
price closes below previous range low
at least N candles hold below range low
ATR normal or expanding
recent structure shows lower highs
breakdown candle has acceptable body strength
```

---

### 8.3 Bullish Continuation

Conditions:

```txt
trend state is short_term_uptrend
pullback does not break prior higher low
EMA alignment supports bullish
price resumes upward movement
```

---

### 8.4 Bearish Continuation

Conditions:

```txt
trend state is short_term_downtrend
pullback does not break prior lower high
EMA alignment supports bearish
price resumes downward movement
```

---

### 8.5 Bullish Reversal

Conditions:

```txt
previous movement bearish
price rejects support/range low
large lower wick appears
follow-through candles close higher
RSI or momentum recovers
```

---

### 8.6 Bearish Reversal

Conditions:

```txt
previous movement bullish
price rejects resistance/range high
large upper wick appears
follow-through candles close lower
RSI or momentum weakens
```

---

### 8.7 Fakeout

Conditions:

```txt
price breaks range
fails to hold outside range
large wick appears
next candles close back inside range
follow-through reverses
```

---

### 8.8 Sideways Range

Conditions:

```txt
price remains inside range
low net movement
mixed highs/lows
ATR compressed or normal
frequent direction changes
```

---

### 8.9 Low-Volatility Chop

Conditions:

```txt
small candle bodies
compressed ATR
low movement efficiency
many direction changes
no clean breakout
```

---

## Done criteria

```txt
Each detector is isolated
Each detector has unit tests
Each detector returns evidence
Golden datasets validate expected patterns
Pattern candidates are persisted
Weak markets do not force bullish/bearish output
```

---

# Phase 9: Signal Classification Engine

## Goal

Select final signal from pattern candidates and feature data.

## Tasks

```txt
Rank pattern candidates
Resolve conflicting patterns
Determine final bias
Determine final pattern
Calculate confidence
Generate evidence
Generate risk notes
Store final signal
```

## Conflict examples

```txt
bullish breakout candidate strength 0.62
fakeout candidate strength 0.66
```

The classifier should select fakeout if failure evidence is stronger.

## Final signal output

```json
{
  "bias": "bullish",
  "patternType": "bullish_breakout",
  "confidenceScore": 0.74,
  "confidenceLabel": "high",
  "pipsMoved": 18.4,
  "movementQuality": "moderate",
  "volatilityState": "expanding",
  "trendState": "short_term_uptrend",
  "rangeState": "above_previous_range",
  "summary": "Bullish breakout detected with expanding volatility."
}
```

## Done criteria

```txt
Final signal is created for completed analysis
No-signal/unclear state works
Confidence components are stored
Signal evidence is stored
Risk notes are stored
Classifier is deterministic
```

---

# Phase 10: Evidence Engine

## Goal

Make every signal explainable.

Evidence should be generated from actual calculated metrics.

## Evidence examples

```txt
Price closed above the previous 60-minute range high for 3 candles.
ATR expanded 1.7x above baseline.
Recent structure formed 6 higher lows.
EMA 9 remained above EMA 21.
RSI moved above 60, supporting bullish momentum.
```

## Evidence rules

Every evidence item must include:

```txt
type
direction
message
weight
source metric
```

## Bad evidence

```txt
AI thinks this is bullish.
```

Never use that.

## Good evidence

```txt
Price closed above the previous range high and held for 3 candles.
```

## Done criteria

```txt
Every signal has at least 3 evidence items when confidence is medium or higher
Every evidence item maps to stored metrics
Contradicting evidence can be stored
Evidence is not generated by LLM
```

---

# Phase 11: Confidence Engine

## Goal

Make confidence transparent and calculated.

## Suggested confidence formula

```txt
pattern_strength: 30%
trend_alignment: 20%
volatility_confirmation: 20%
indicator_support: 15%
data_quality: 10%
news_context: 5%
```

For pre-news phase:

```txt
news_context = 0
or redistribute weight proportionally
```

Better for MVP:

```txt
pattern_strength: 35%
trend_alignment: 20%
volatility_confirmation: 20%
indicator_support: 15%
data_quality: 10%
```

## Confidence labels

```txt
0.00–0.39 low
0.40–0.64 medium
0.65–0.79 high
0.80–1.00 very_high
```

## Done criteria

```txt
Confidence score is stored
Every confidence component is stored
Low data quality reduces confidence
Mixed indicators reduce confidence
Strong pattern + strong trend + strong volatility increases confidence
```

---

# Phase 12: Risk Notes Engine

## Goal

Generate cautionary notes from data.

Risk notes are important because trading analysis must not feel overconfident.

## Risk notes examples

```txt
Move occurred during high volatility.
Data quality is below ideal threshold.
Signal appeared near a potential news window.
Price moved far from the range, increasing pullback risk.
Market structure is mixed despite bullish movement.
Volatility spike may indicate unstable conditions.
```

## Done criteria

```txt
Risk notes are generated deterministically
Risk notes are stored
High-risk signals include visible risk notes
No signal is presented as guaranteed
```

---

# Phase 13: Deterministic Explanation Engine

## Goal

Generate non-LLM summaries first.

This should always run, even when LLM is disabled.

## Example output

```txt
EUR/USD showed bullish movement during the selected window. Price moved +18.4 pips, closed above the previous range high, and volatility expanded above baseline. Confidence is high because range behavior, short-term trend structure, and volatility all support the same direction.
```

## Why this is important

```txt
works without AI provider
cheaper
consistent
testable
safe
fallback for LLM failure
```

## Done criteria

```txt
Every signal gets deterministic explanation
No financial advice wording
No buy/sell command
No invented facts
Template version is stored
```

---

# Phase 14: LLM Explanation Layer

## Goal

Use AI only for natural-language explanation.

## LLM receives

```txt
final signal
evidence
confidence components
risk notes
feature summary
indicator summary
news correlation if available
```

## LLM must not receive raw instruction like

```txt
Tell me if this is bullish or bearish.
```

That is banned.

## Correct prompt role

```txt
You are explaining a precomputed market analysis.
Do not calculate new values.
Do not invent facts.
Do not provide financial advice.
Explain only the supplied evidence.
Use cautious market-analysis language.
```

## Safety validator

After LLM output, scan for banned language:

```txt
buy now
sell now
guaranteed
risk-free profit
must enter
cannot lose
use leverage
```

If unsafe, block and use deterministic explanation.

## Done criteria

```txt
LLM explanation is stored
Prompt input is stored
Prompt version is stored
Token usage is stored
Unsafe output is blocked
Fallback works
LLM cannot override signal
```

---

# Phase 15: News/Event Correlation Engine

## Goal

Correlate market movement with possible events.

This is not first priority. Add after core signal engine is solid.

## Inputs

```txt
signal timestamp
signal symbol
asset/currency relevance
event time
event importance
price movement size
volatility expansion
sentiment if available
```

## Correlation score components

```txt
time proximity: 30%
asset/currency relevance: 25%
event importance: 20%
movement magnitude: 15%
sentiment alignment: 10%
```

## Labels

```txt
none
weak
possible
strong
```

## Language rule

Allowed:

```txt
Possible correlation detected.
The movement happened near a high-impact USD event.
The event may have contributed to volatility.
```

Not allowed:

```txt
This event definitely caused the move.
```

## Done criteria

```txt
News events can be ingested
News events map to symbols
Correlation score is calculated
Correlation is stored
Signal explanation includes cautious correlation wording
```

---

# Phase 16: Analysis Replay and Engine Versioning

## Goal

Make backend auditable and upgrade-safe.

When rules change, old signals should remain traceable.

## Required behavior

Each analysis run stores:

```txt
engine version
rule set version
threshold config
feature snapshot
indicator snapshot
pattern candidates
final signal
evidence
confidence components
explanation
```

## Replay feature

Add internal endpoint:

```txt
POST /analysis-runs/{id}/replay
```

Modes:

```txt
same_engine_version
latest_engine_version
```

This helps compare old logic vs new logic.

## Done criteria

```txt
Every analysis has engine version
Rule config is stored
Old analysis can be inspected
Replay can run against stored candle data
```

---

# Phase 17: Golden Dataset Test Suite

## Goal

Create industry-grade confidence in the intelligence layer.

## Golden datasets

Create these:

```txt
bullish_breakout_eurusd_1m.csv
bearish_breakdown_eurusd_1m.csv
bullish_fakeout_eurusd_1m.csv
bearish_fakeout_eurusd_1m.csv
sideways_chop_eurusd_1m.csv
high_volatility_spike_eurusd_1m.csv
jpy_pair_pip_test_usdjpy_1m.csv
crypto_tick_test_btcusdt_1m.csv
bad_data_invalid_ohlc.csv
missing_candles.csv
```

## Expected outputs

Each golden dataset should specify:

```txt
expected bias
expected pattern
expected confidence range
expected pips direction
expected volatility state
expected risk notes
```

Example:

```json
{
  "dataset": "bullish_breakout_eurusd_1m.csv",
  "expectedBias": "bullish",
  "expectedPattern": "bullish_breakout",
  "confidenceRange": [0.65, 0.85],
  "expectedVolatilityState": "expanding"
}
```

## Done criteria

```txt
Golden tests run in CI
Pattern detection cannot regress silently
Bad data test passes
Insufficient data test passes
Pip/tick tests pass
```

---

# Phase 18: Backend Observability

## Goal

Production backend must be inspectable.

## Logs

Log:

```txt
import started
import completed
import failed
analysis created
analysis running
candles loaded
features calculated
patterns detected
signal classified
LLM explanation generated
analysis completed
analysis failed
```

## Metrics

Track:

```txt
import duration
analysis duration
worker queue depth
failed job count
average candles per analysis
LLM latency
LLM cost
database query latency
pattern distribution
confidence distribution
```

## Alerts

Create alerts for:

```txt
worker down
Neon connection failure
high failed-job rate
LLM provider failure
analysis latency spike
queue backlog
```

## Done criteria

```txt
Failed analysis can be diagnosed
Slow analysis can be identified
LLM cost is visible
Worker health is visible
Database errors are visible
```

---

# Phase 19: Backend Security and Safety

## Goal

Protect data and prevent unsafe financial output.

## API security

```txt
auth required for protected APIs
workspace isolation
admin route protection
rate limits
request size limits
file upload limits
input validation
SQL injection prevention through ORM/bound params
```

## Secret security

```txt
Neon URL in environment only
LLM keys in environment only
no provider keys exposed in API responses
no secrets in logs
```

## LLM safety

```txt
banned phrase filter
financial advice filter
fallback explanation
prompt versioning
output storage
```

## Done criteria

```txt
users cannot access other workspace data
large uploads are controlled
unsafe LLM outputs are blocked
API keys are never exposed
audit logs exist for critical actions
```

---

# Phase 20: Performance Planning for Neon

## Goal

Keep Neon efficient.

## Early optimization rules

```txt
index candle queries properly
always filter by workspace_id + symbol_id + timeframe + timestamp
avoid loading unnecessary columns
fetch only needed windows
use batch inserts for candles
use COPY-style ingestion if needed
avoid per-row DB writes in import workers
store large raw files outside DB
store metadata in DB
```

## Candle query pattern

Most common query:

```txt
WHERE workspace_id = ?
AND symbol_id = ?
AND timeframe = ?
AND timestamp BETWEEN ? AND ?
ORDER BY timestamp ASC
```

Create index exactly for that.

## Done criteria

```txt
10k candle import does not timeout
100k candle import is handled through background job
analysis query returns quickly for normal windows
database indexes are verified
```

---

# 21. Final Backend Build Order

Build exactly in this order:

```txt
1. FastAPI + Neon foundation
2. Symbol metadata
3. Import batches
4. Candle validation
5. Candle storage
6. Candle query/quality layer
7. Analysis run lifecycle
8. Feature engineering engine
9. Indicator engine
10. Pattern detection engine
11. Signal classifier
12. Evidence engine
13. Confidence engine
14. Risk notes engine
15. Deterministic explanation engine
16. LLM explanation engine
17. News/event correlation engine
18. Engine versioning and replay
19. Golden dataset test suite
20. Observability
21. Security hardening
22. Performance tuning
```

Do not skip steps.

---

# 22. What the Backend Should Return to UI Later

The future UI should not need to calculate anything.

The backend should return a complete analysis object.

Example final response:

```json
{
  "analysisRun": {
    "id": "run_123",
    "status": "completed",
    "symbol": "EURUSD",
    "timeframe": "1m",
    "startTime": "2026-04-29T09:00:00Z",
    "endTime": "2026-04-29T10:00:00Z"
  },
  "signal": {
    "id": "sig_123",
    "bias": "bullish",
    "patternType": "bullish_breakout",
    "confidenceScore": 0.74,
    "confidenceLabel": "high",
    "pipsMoved": 18.4,
    "movementQuality": "moderate",
    "volatilityState": "expanding",
    "trendState": "short_term_uptrend",
    "rangeState": "above_previous_range",
    "summary": "Bullish breakout detected with expanding volatility."
  },
  "evidence": [
    {
      "type": "range_break",
      "direction": "supports_bullish",
      "message": "Price closed above the previous 60-minute range high for 3 candles.",
      "weight": 0.25
    },
    {
      "type": "volatility",
      "direction": "supports_bullish",
      "message": "ATR expanded 1.7x above baseline.",
      "weight": 0.2
    }
  ],
  "confidence": {
    "components": [
      {
        "name": "pattern_strength",
        "score": 0.82,
        "weight": 0.35
      },
      {
        "name": "trend_alignment",
        "score": 0.76,
        "weight": 0.2
      }
    ]
  },
  "riskNotes": [
    "Move occurred during elevated volatility."
  ],
  "explanation": {
    "deterministic": "EUR/USD showed bullish movement during the selected window...",
    "ai": "EUR/USD is showing bullish pressure because price broke above the previous range..."
  }
}
```

This is the ideal backend contract.

---

# 23. The Most Important Backend Rules

## Rule 1

Do not let the LLM classify the market.

## Rule 2

Do not classify without enough candle data.

## Rule 3

Do not force bullish/bearish if the market is unclear.

## Rule 4

Store every intermediate artifact.

## Rule 5

Every signal must have evidence.

## Rule 6

Confidence must be calculated, not guessed.

## Rule 7

News correlation must use cautious language.

## Rule 8

Old analysis must remain explainable after engine updates.

## Rule 9

Golden dataset tests must protect the intelligence layer.

## Rule 10

The UI should be dumb later. The backend should be smart.

---

# Final Backend Vision

The backend should become a reliable intelligence engine like this:

```txt
Candle data
→ validation
→ Neon storage
→ data quality scoring
→ feature engineering
→ indicator calculations
→ pattern candidates
→ signal classification
→ evidence generation
→ confidence scoring
→ risk notes
→ deterministic explanation
→ optional AI explanation
→ stored auditable result
→ clean API response
```

That is the production-grade backend worth building.

The weak version would be:

```txt
candles → GPT → answer
```

The strong version is:

```txt
candles → deterministic intelligence engine → evidence-backed signal → AI explanation
```

That is exactly how this should be built.
