# Demo Mode

Demo mode creates repeatable synthetic product smoke data for local or staging validation.

It can:

- create or reuse a demo workspace and demo operator user
- seed configured symbols and a demo JSON import source
- generate deterministic synthetic candles without external providers
- import candles through the existing JSON import path
- run deterministic analysis and signal classification
- build setup context, score review priority, and evaluate observed outcomes
- create demo watchlist and scan artifacts
- create a persisted daily brief
- optionally create a journal observation

Enablement:

```bash
DEMO_MODE_ENABLED=true
DEMO_MODE_DEFAULT_WORKSPACE_NAME="Demo Workspace"
DEMO_MODE_DEFAULT_SYMBOLS=BTCUSDT,ETHUSDT,EURUSD
DEMO_MODE_DEFAULT_TIMEFRAMES=1m,5m
```

`APP_ENV=development` also enables demo mode. When disabled, `/demo-mode/status`,
`/demo-mode/workspace`, and `/demo-mode/run-full-flow` return clean disabled responses.

API:

- `GET /demo-mode/status`
- `POST /demo-mode/workspace`
- `POST /demo-mode/run-full-flow`

CLI:

```bash
python -m app.cli demo run-full-flow
```

Safety boundaries:

- demo data is synthetic and deterministic
- demo artifacts are labeled with `demo=true` metadata where existing models support metadata
- no external provider credentials are required
- no broker execution or auto-trading exists in the flow
- no financial advice is generated
- destructive behavior is explicit; the flow writes normal demo artifacts to the configured database

No new demo tables are used. The flow reuses existing workspace, symbol, data source, import,
candle, analysis, signal, setup context, priority, outcome, watchlist, scan, daily brief, readiness,
and journal records.
