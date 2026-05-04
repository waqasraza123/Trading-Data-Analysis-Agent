# Personal Strategy Preference Profiles

Personal strategy preference profiles let a workspace or user define review preferences for stored deterministic market-intelligence artifacts.

They are filters only. They do not mutate deterministic strategy profiles, change signal classification, run analysis, evaluate outcomes, send notifications, call brokers, auto-trade, copy-trade, or provide financial advice.

## Table

`personal_strategy_preference_profiles`

Important fields:

- `workspace_id`: required workspace owner.
- `user_id`: optional user owner inside the workspace.
- `status`: `active`, `paused`, or `archived`.
- `is_default`: default review profile for the workspace.
- `market_types_json`, `symbol_ids_json`, `excluded_symbol_ids_json`
- `timeframes_json`, `session_labels_json`
- `pattern_types_json`, `excluded_pattern_types_json`
- `strategy_profile_keys_json`
- `minimum_confidence`, `minimum_setup_quality`, `max_stale_seconds`
- `require_fresh_data`, `require_timeframe_agreement`, `require_acceptable_data_quality`
- `include_news_context`, `include_outcomes`
- `notification_preferences_json`, `metadata_json`

## API

```txt
POST /preference-profiles
GET /preference-profiles?workspaceId=<workspace-id>
GET /preference-profiles/default?workspaceId=<workspace-id>
GET /preference-profiles/{profile_id}
PATCH /preference-profiles/{profile_id}
POST /preference-profiles/{profile_id}/archive
POST /preference-profiles/{profile_id}/set-default
GET /preference-profiles/{profile_id}/filter-context
POST /preference-profiles/{profile_id}/match-signal/{signal_id}
```

## Matcher Behavior

The matcher reads the preference profile, signal, symbol metadata, setup context, market session context, and market memory when available.

It returns:

- `matches`: whether the signal passes the preference profile.
- `included_reasons`: preferences that were satisfied.
- `excluded_reasons`: preferences that blocked the signal from the review scope.
- `preference_warnings`: optional context that was missing or preferred but unavailable.

Missing optional context is handled safely. Explicit requirements such as fresh data, acceptable data quality, minimum setup quality, and timeframe agreement can exclude a signal when the required context is unavailable.

`PREFERENCE_PROFILE_DEFAULT_MAX_STALE_SECONDS` defaults to `7200` and is applied when a profile
requires fresh data without an explicit stale-data window.

The web command center and triage board use the selected or default preference profile as review
scope. If profile endpoints are unavailable, those pages keep the unfiltered deterministic review
workflow.

## Safety Boundary

Preference profiles personalize review workflows only. They are not strategy profiles, classifiers, execution rules, alerts, broker workflows, account logic, or advice. Deterministic source artifacts remain authoritative.
