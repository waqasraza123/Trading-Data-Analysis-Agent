# News Event Correlation

This slice adds deterministic market/economic/news event context. It stores structured events,
maps them to symbols, scores possible proximity to completed or in-progress lifecycle signals, and
persists auditable correlation rows.

It does not add external paid news providers, UI, broker execution, alerts, auto-trading, billing,
copy/social trading, or LLM-based classification.

## Purpose

News/event correlation is contextual. It can say:

```txt
possible correlation
weak correlation
strong possible correlation
event happened near the move
event may have contributed to volatility
```

It must not say:

```txt
the event definitely caused the move
certain cause
confirmed reason
trade because of this news
```

The signal classifier remains deterministic and unchanged. News context does not override signal
classification, confidence, or trade direction.

## Tables

`news_events` stores normalized manual/imported event records:

```txt
workspace_id nullable
source
event_type
title
description
event_time
timezone
currency
asset
symbol_id
importance
sentiment
actual_value
forecast_value
previous_value
impact_json
url
raw_payload_json
created_at
updated_at
```

`signal_news_correlations` stores scored context for completed signals and signals being processed
inside the analysis lifecycle:

```txt
workspace_id
analysis_run_id
signal_id
news_event_id
correlation_score
correlation_label
time_delta_minutes
direction_alignment
volatility_reaction
relevance_score
importance_score
magnitude_score
sentiment_score
reason
metadata_json
created_at
```

Correlation metadata includes scorer version, weights, window config, relevance reason, magnitude
inputs, and sentiment handling.

## Event Ingestion

Create one event:

```txt
POST /news-events
```

Import a JSON list:

```txt
POST /news-events/import-json
```

Example:

```json
[
  {
    "source": "manual",
    "eventType": "economic_calendar",
    "title": "USD CPI Release",
    "description": "US inflation data release",
    "eventTime": "2026-04-29T12:30:00Z",
    "currency": "USD",
    "importance": "high",
    "sentiment": "unknown",
    "actualValue": "3.4",
    "forecastValue": "3.2",
    "previousValue": "3.1"
  }
]
```

Validation behavior:

```txt
title required
source required
event_time required and normalized to UTC
event_type defaults to manual
importance defaults to unknown
sentiment defaults to unknown
currency and asset normalize to uppercase
raw_payload_json preserves the original payload values when omitted
```

Query/update:

```txt
GET /news-events
GET /news-events/{news_event_id}
PATCH /news-events/{news_event_id}
```

## Relevance Rules

An event is relevant when it deterministically maps to the signal symbol:

```txt
exact symbol_id match = 1.00
asset equals symbol string = 0.90
base asset/currency match = 0.75
quote asset/currency match = 0.65
USD macro event on USD pair = 0.70
global critical event with no symbol/currency/asset = 0.40
no match = 0.00
```

## Scoring Formula

Default window:

```txt
NEWS_CORRELATION_PRE_EVENT_MINUTES = 5
NEWS_CORRELATION_POST_EVENT_MINUTES = 30
NEWS_CORRELATION_MAX_EVENTS_PER_SIGNAL = 10
```

Weighted score:

```txt
time proximity = 30%
relevance = 25%
event importance = 20%
movement magnitude = 15%
sentiment/direction alignment = 10%
```

Labels:

```txt
0.00-0.24 none
0.25-0.49 weak
0.50-0.74 possible
0.75-1.00 strong
```

Unknown sentiment receives a neutral score and metadata:

```txt
sentimentKnown = false
handling = neutral_score
```

If the feature snapshot is missing, scoring degrades instead of failing.

## Correlation APIs

Run/read by analysis run:

```txt
POST /analysis-runs/{analysis_run_id}/correlate-news
GET /analysis-runs/{analysis_run_id}/news-correlations
```

Run/read by signal:

```txt
POST /signals/{signal_id}/correlate-news
GET /signals/{signal_id}/news-correlations
```

Correlation is idempotent for the current signal: existing rows for the signal are replaced before
new rows are persisted.

## Lifecycle Hook

If `include_news_correlation=true`, the analysis lifecycle runs correlation after signal
classification and before deterministic explanation generation. If `include_ai_explanation=true`
as well, this ordering guarantees the LLM can only see news that has already been persisted as
signal news correlations. If false, it skips news context.

When a strong correlation is persisted, the service adds a small risk note:

```txt
A relevant market event occurred near this signal window. Volatility may be event-driven.
```

Confidence and classification are not changed.

Audit events include:

```txt
news_correlation_started
news_correlation_completed
news_correlation_failed
```
