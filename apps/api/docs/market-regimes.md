# Market Regime Context

Market regime context records deterministic market-background labels for an existing analysis run
or signal. The module is backend-only and supports operator review of persisted intelligence
artifacts; it does not classify signals, override signals, execute actions, send notifications, or
provide financial advice.

## Purpose

The regime engine stores contextual labels such as trend state, volatility state, range state, and
data-quality context around already persisted deterministic analysis artifacts.

Expected routes:

```txt
POST /analysis-runs/{analysis_run_id}/market-regime
GET /analysis-runs/{analysis_run_id}/market-regime
POST /signals/{signal_id}/market-regime
GET /signals/{signal_id}/market-regime
```

## Settings

```txt
MARKET_REGIME_VERSION=market_regime_v1
MARKET_REGIME_MIN_CONFIDENCE=0.5000
MARKET_REGIME_STRONG_DATA_QUALITY=0.8500
MARKET_REGIME_ACCEPTABLE_DATA_QUALITY=0.6500
```

## Integration

Decision readiness may read the latest persisted regime context when available. Historical case
vector generation may include regime fields when they already exist, but it must not generate a
regime implicitly.

## Safety

Regime context is diagnostic market background only. It must not mutate signals, strategy profiles,
pattern candidates, action plans, outcomes, reports, timelines, or quality gate results.
