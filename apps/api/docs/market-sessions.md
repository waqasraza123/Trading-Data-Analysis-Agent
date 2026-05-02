# Market Session Context Engine

Market session context attaches deterministic session labels to analysis runs and signals. It helps
operators compare observed outcomes and readiness context across recurring market windows.

## APIs

```txt
POST /analysis-runs/{analysis_run_id}/market-session
GET /analysis-runs/{analysis_run_id}/market-session
POST /signals/{signal_id}/market-session
GET /signals/{signal_id}/market-session
```

## Labels

```txt
asia
london
new_york
overlap
off_hours
unknown
```

## Settings

```txt
MARKET_SESSION_VERSION=v1
MARKET_SESSION_DEFAULT_TIMEZONE=UTC
```
