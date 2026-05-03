# Data Quality Intelligence Monitor

The data quality monitor creates backend-only quality runs and findings for candle ranges, data
sources, and live subscriptions. It is diagnostic context for operators and downstream readiness or
dataset workflows.

It does not mutate candles, signals, strategy profiles, outcomes, diagnostics, alerts, broker state,
or execution behavior.

## APIs

```txt
POST /data-quality/candle-range/run
POST /data-quality/data-sources/{source_id}/run
POST /data-quality/live-subscriptions/{subscription_id}/run
GET /data-quality/runs/{run_id}
GET /data-quality/runs/{run_id}/findings
```

## Labels

```txt
strong
acceptable
degraded
poor
insufficient_data
```

The label can be included in decision readiness, intelligence quality, and dataset exports as
compact context. Full finding payloads are not exported by default.

## Settings

```txt
DATA_QUALITY_VERSION=v1
DATA_QUALITY_STRONG_THRESHOLD=0.9500
DATA_QUALITY_ACCEPTABLE_THRESHOLD=0.8500
DATA_QUALITY_DEGRADED_THRESHOLD=0.7000
DATA_QUALITY_OUTLIER_RANGE_MULTIPLIER=5.0000
DATA_QUALITY_STALE_LIVE_SECONDS=300
```
