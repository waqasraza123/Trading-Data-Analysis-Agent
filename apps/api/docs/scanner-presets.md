# Scanner Presets

Scanner presets are operator templates for quickly creating market watchlists and scheduled scan
configs. They are configuration helpers only. Applying a preset does not run a scan, create a
signal setup, send alerts, call brokers, or provide financial advice.

## Scope

Implemented:

```txt
versioned scanner preset catalog
default preset seeding
workspace-aware preset listing
preset detail lookup by key
apply preset audit records
watchlist creation from selected symbols or active preset templates
scheduled scan config creation from preset templates
application warnings for missing template symbols or skipped creation options
```

Presets create passive records. A scan runs only through the existing explicit scanner controls,
such as `POST /scheduled-scan-configs/{scan_config_id}/run`, `POST /scheduled-scan-configs/run-due`,
or the scheduled scan worker when a config later becomes due.

In the daily workflow, presets sit after data freshness review and before explicit scan execution.
They are shortcuts for creating repeatable watchlist/session review configuration, not automation
that runs analysis on apply.

## Settings

```txt
SCANNER_PRESET_VERSION=v1
```

The default seed endpoint and seed command use this version when inserting or refreshing default
preset rows.

## Tables

`scanner_presets` stores reusable preset definitions:

```txt
id
workspace_id nullable
key
name
description
category
status
preset_version
market_types_json
symbol_templates_json
timeframe_templates_json
session_filters_json
scan_config_template_json
watchlist_template_json
preference_profile_filters_json
metadata_json
created_at
updated_at
```

`scanner_preset_applications` stores every apply attempt that reaches record creation:

```txt
id
workspace_id
scanner_preset_id
status
watchlist_id nullable
scan_config_id nullable
preference_profile_id nullable
applied_config_json
error_message nullable
created_at
updated_at
```

Preset categories:

```txt
session
market
volatility
pattern_context
data_repair
review
```

Preset statuses:

```txt
active
archived
```

Application statuses:

```txt
completed
completed_with_warnings
failed
```

## Default Presets

The default seed creates these v1 presets:

```txt
london_open
new_york_open
crypto_24h
high_volatility
trend_continuation
reversal_risk
range_no_directional
needs_confirmation
stale_data_repair
close_of_day_review
```

Each preset defines market types, symbol templates, timeframe templates, optional session filters,
watchlist item defaults, scan config defaults, preference-profile filter hints, and safety
metadata.

## API

```txt
GET /scanner-presets
GET /scanner-presets/{preset_key}
POST /scanner-presets/seed-default
POST /scanner-presets/{preset_id}/apply
GET /scanner-presets/applications/{application_id}
```

List query parameters:

```txt
workspace_id optional
category optional
```

Preset detail query parameters:

```txt
workspace_id optional
```

Apply request:

```json
{
  "workspaceId": "00000000-0000-0000-0000-000000000000",
  "symbolIds": ["00000000-0000-0000-0000-000000000001"],
  "sourceId": null,
  "preferenceProfileId": null,
  "timeframes": ["5m", "15m"],
  "createWatchlist": true,
  "createScanConfig": true,
  "nameOverride": null
}
```

The API accepts camelCase or snake_case request fields through the shared schema base.

## Apply Behavior

Apply behavior is intentionally bounded:

- Selected `symbolIds` are used first when provided.
- If no symbols are selected, the service resolves preset `symbol_templates_json` against active
  stored symbols.
- Missing template symbols are warnings, not implicit symbol creation.
- Timeframes are validated against the backend `Timeframe` enum.
- A provided source must belong to the workspace and be active.
- A provided preference profile must belong to the workspace.
- Watchlist items are created for each resolved symbol and selected timeframe when watchlist
  creation is requested.
- Scan config creation uses watchlist mode when a watchlist was created.
- If scan config creation is requested without watchlist creation, the service creates a
  single-symbol scan config from the first resolved symbol/timeframe and records a warning when more
  targets were selected.
- Applying a preset never invokes the scan executor.

## Safety

Scanner presets do not:

```txt
run scans on apply
send alerts or notifications
execute broker actions
place orders
auto-trade
copy trade
create directional execution setups
provide financial advice
fetch external market data
override deterministic signals
```

The generated watchlists and scan configs are review workflow configuration. Existing run controls
remain explicit and separate.
