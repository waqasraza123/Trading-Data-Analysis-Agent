# Event Studies

Event studies measure observed candle behavior around persisted news events. They are deterministic
analysis artifacts for context and review.

This module does not claim that an event caused a movement. Public responses and reports should use
terms such as observed reaction, possible relationship, pre-event window, and post-event window.

## Tables

- `event_study_runs`
- `event_study_results`

## Settings

```txt
EVENT_STUDY_VERSION=v1
EVENT_STUDY_DEFAULT_PRE_EVENT_MINUTES=60
EVENT_STUDY_DEFAULT_POST_EVENT_MINUTES=240
EVENT_STUDY_MIN_CANDLES=5
EVENT_STUDY_STRONG_REACTION_MULTIPLIER=2.0
EVENT_STUDY_MODERATE_REACTION_MULTIPLIER=1.25
```

## APIs

```txt
POST /event-studies/run
GET /event-studies/runs/{run_id}
GET /event-studies/runs/{run_id}/results
GET /news-events/{news_event_id}/event-studies
```

## Limitations

- Uses stored candles and persisted news/event context only.
- Does not modify news correlation, signals, outcomes, strategy profiles, or reasoning output.
- Does not provide financial advice, broker execution, alerts, or auto-trading behavior.
