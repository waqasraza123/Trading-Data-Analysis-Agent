# Daily Briefs

Daily briefs persist a deterministic daily, session, intraday, watchlist, or custom-period market-intelligence brief for a workspace. The module is the backend contract for the daily command center and `/brief` page.

The brief is not broker execution, not auto-trading, not financial advice, and not a directional-action service. It only reads existing persisted artifacts and writes `daily_brief_runs` plus `daily_brief_items`.

## Sources

The builder composes stored artifacts when present:

- Signal digests.
- Market memory.
- Signal priority scores.
- Setup context.
- Provider health, data quality, and latest final candle timestamps.
- Signal outcomes.
- Backend-safe action items and scheduled scan configs.
- Decision readiness.
- Market regimes, sessions, multi-timeframe context, and cross-asset context.
- Journal entries.

Generation does not trigger scans, provider polling, outcome evaluation, LLM calls, notifications, or action execution.

In the daily product flow, the brief is read after data freshness review, explicit workflow run,
scanner preset setup, and deterministic scan completion. It remains a stored summary over existing
artifacts and never becomes an execution or notification trigger.

## Sections

- `summary`: counts for symbols reviewed, fresh symbols, stale/degraded symbols, review-first items, confirmation items, avoid conditions, recent outcomes, and pending backend actions.
- `review_first`: deterministic high-priority review contexts, using signal priority scores when available and signal confidence/setup quality as fallback.
- `needs_confirmation`: medium-confidence, mixed-context, wait-condition, pending-outcome, or readiness-review items.
- `avoid_conditions`: no directional signal, stale data, conflicting evidence, low data quality, range/chop/fakeout context, or unresolved review blockers.
- `data_freshness`: provider health, market memory freshness, latest final candle timestamps, and data-quality issues.
- `outcome_updates`: observed follow-through, observed reversal, no observed follow-through, insufficient data, and related outcome states.
- `watch_next`: backend-safe observations such as monitor final candle close, inspect data freshness, review evidence, evaluate outcome after horizon, or request human review.
- `pending_actions`: backend-safe action items and due scheduled scans, listed only.
- `market_context`: market regime, market session, multi-timeframe, and cross-asset context that matters for the review period.

## API

```txt
POST /daily-briefs
POST /daily-briefs/daily
POST /daily-briefs/session
POST /daily-briefs/watchlist
GET /daily-briefs
GET /daily-briefs/{brief_id}
GET /daily-briefs/{brief_id}/items
GET /workspaces/{workspace_id}/daily-brief/latest
```

Generic request:

```json
{
  "workspaceId": "uuid",
  "briefType": "daily",
  "periodStart": "2026-05-03T00:00:00Z",
  "periodEnd": "2026-05-03T23:59:59Z",
  "timezone": "UTC",
  "watchlistId": null,
  "filters": {
    "symbolIds": [],
    "timeframes": [],
    "preferenceProfileId": null
  }
}
```

## Persistence

- `daily_brief_runs` stores brief metadata, filters, summary JSON, section JSON, warnings, and optional linked signal digest.
- `daily_brief_items` stores item rows for review, confirmation, avoid, stale-data, outcome, watch-next, action, market-context, data-quality, and journal-follow-up sections.

Indexes support workspace/type/latest queries, watchlist/latest queries, brief item type lookups, priority lookups, signal lookups, and symbol lookups.

## Settings

- `DAILY_BRIEF_VERSION`, default `v1`.
- `DAILY_BRIEF_DEFAULT_TIMEZONE`, default `UTC`.
- `DAILY_BRIEF_MAX_ITEMS`, default `150`.
- `DAILY_BRIEF_REVIEW_FIRST_LIMIT`, default `20`.
- `DAILY_BRIEF_OUTCOME_UPDATE_LIMIT`, default `20`.
- `DAILY_BRIEF_ACTION_ITEM_LIMIT`, default `30`.

## Safe Language

Allowed language includes bullish bias, bearish bias, neutral, no directional signal, setup context, invalidation context, observation zone, target context zone, review recommended, needs confirmation, avoid condition, stale data, conflicting evidence, observed follow-through, observed reversal, and watch next.

The builder sanitizes unsafe direct-order instructions, leverage prompts, certainty claims, account-result claims, and external alert wording.

## Frontend

The web `/brief` and `/command-center` paths prefer `GET /workspaces/{workspace_id}/daily-brief/latest` when a completed backend run exists. If the endpoint is missing, unavailable, or no latest run exists, the web app keeps the existing frontend fallback composition over individual optional endpoints.
