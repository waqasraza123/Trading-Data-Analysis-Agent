# Signal Digests

Signal digests persist deterministic daily, session, custom-period, and watchlist summaries from
already stored backend artifacts. They are for operator review and future dashboard surfaces.

They answer:

- what changed since the selected review window started
- which symbols have bullish bias, bearish bias, neutral context, or no directional signal
- which persisted signals have the strongest deterministic confidence and evidence context
- which signals are blocked, conflicted, stale, or review-recommended
- which outcomes recently completed with observed follow-through, observed reversal, or no observed follow-through
- which news or event correlations may matter without implying causation
- which backend follow-up records are pending or due
- which setups should be watched, avoided, or reviewed using safe non-advisory language

Signal digests are not a newsletter, financial-advice layer, notification system, alerting system,
broker integration, auto-trading workflow, copy-trading workflow, or LLM generation path.

## Persistence

`signal_digest_runs` stores the digest header:

- workspace
- digest type
- status
- digest version
- title
- period start and end
- timezone
- filters JSON
- executive summary JSON
- section count JSON
- warnings JSON

`signal_digest_items` stores bounded section items linked back to source artifacts when available:

- signal
- analysis run
- outcome
- action item
- news event
- symbol

Source artifacts remain authoritative. Digest generation creates only digest run and item records.
It does not mutate signals, outcomes, action items, quality gates, market memory, watchlists,
scheduled scans, readiness assessments, profiles, or classifier behavior.

## Digest Types

- `daily`
- `session`
- `custom_period`
- `watchlist`

## Sections

Executive summary:

- total signal count
- bullish, bearish, neutral, and no-signal counts
- review-recommended count
- stale or degraded data count
- recent outcome update count

Top directional bias:

- high-confidence bullish bias or bearish bias context
- sorted by deterministic confidence, evidence count, and freshness
- safe summary only

No-signal and avoid conditions:

- no directional signal
- low data quality
- conflicting evidence
- fakeout risk
- chop or range context
- stale candles

Outcome updates:

- observed follow-through
- observed reversal
- no observed follow-through
- insufficient future data

News and event context:

- possible correlations only
- no causation claims

Pending backend follow-up:

- pending or due action items
- due scheduled scan configs
- human review requested
- wait for more final candles
- evaluate outcome after horizon
- run news correlation

Data quality and freshness warnings:

- stale market memory
- degraded or poor data quality
- no-data freshness state

Watch conditions:

- wait for final candle close
- review evidence
- inspect data quality
- evaluate outcome after horizon
- run news correlation
- request human review

Digest generation only lists these conditions. It does not trigger them.

## Safe Language

Allowed digest language includes:

- bullish bias
- bearish bias
- no directional signal
- setup quality
- review recommended
- watch condition
- avoid reason
- stale data
- conflict
- observed follow-through
- observed reversal

Digest builders sanitize blocked wording and avoid directive or certainty language. LLMs are not
used to generate or classify digest content.

## API

Create a custom digest:

```txt
POST /signal-digests
```

Request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "digestType": "daily",
  "periodStart": "2026-05-03T00:00:00Z",
  "periodEnd": "2026-05-04T00:00:00Z",
  "timezone": "UTC",
  "filters": {
    "watchlistId": null,
    "symbolIds": [],
    "timeframes": ["1m", "5m"]
  },
  "maxItems": 100
}
```

List digests:

```txt
GET /signal-digests?workspaceId=...&digestType=daily&status=completed
```

Read one digest:

```txt
GET /signal-digests/{digest_id}
```

Read digest items:

```txt
GET /signal-digests/{digest_id}/items
GET /signal-digests/{digest_id}/items?itemType=top_bias
```

Create a daily digest:

```txt
POST /signal-digests/daily
```

Request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "date": "2026-05-03",
  "timezone": "UTC",
  "filters": {
    "watchlistId": null,
    "symbolIds": [],
    "timeframes": ["1m", "5m"]
  },
  "maxItems": 100
}
```

Create a session digest:

```txt
POST /signal-digests/session
```

Request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "sessionLabel": "london",
  "date": "2026-05-03",
  "timezone": "UTC",
  "filters": {
    "watchlistId": null,
    "symbolIds": [],
    "timeframes": ["5m"]
  },
  "maxItems": 100
}
```

## Settings

- `SIGNAL_DIGEST_VERSION`, default `v1`
- `SIGNAL_DIGEST_DEFAULT_TIMEZONE`, default `UTC`
- `SIGNAL_DIGEST_MAX_ITEMS`, default `100`
- `SIGNAL_DIGEST_HIGH_CONFIDENCE_THRESHOLD`, default `0.70`
- `SIGNAL_DIGEST_STALE_DATA_PRIORITY`, default `high`

## Future Integration

Future dashboard or alert integrations may read digest runs and items, but this module does not
send notifications, email, Telegram, Discord, webhook deliveries, broker actions, or external
messages. Any future delivery path must preserve safe wording, deterministic provenance, and the
no-financial-advice boundary.
