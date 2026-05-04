# Deterministic Synthetic Candle Fixtures

The synthetic fixture generator creates repeatable OHLC candle sequences for backend QA, parser validation, demos, and future golden tests.

It is development and testing support only. It does not fetch external data, mutate production data, run analysis, call providers, send alerts, execute broker actions, auto-trade, or provide financial advice.

## Purpose

The generator provides deterministic candle inputs for:

- backend import parser validation;
- future golden intelligence fixtures;
- data quality and missing-candle scenario checks;
- chart screenshot parser comparison examples;
- demo payloads that do not depend on external market data.

## Patterns

Supported pattern values:

- `bullish_breakout`
- `bearish_breakdown`
- `bullish_continuation`
- `bearish_continuation`
- `bullish_reversal`
- `bearish_reversal`
- `fakeout`
- `sideways_range`
- `low_volatility_chop`
- `high_volatility_spike`
- `missing_candle_gap`
- `jpy_pair_pip_sample`
- `crypto_tick_sample`

Malformed candles are optional through `includeMalformed=true`. Normal generated candles satisfy OHLC invariants:

```txt
high >= max(open, close)
low <= min(open, close)
```

Malformed output deliberately violates those rules for parser and validation checks.

## Determinism

Generation uses an explicit seed. If no seed is supplied, the backend uses:

```txt
SYNTHETIC_FIXTURES_DEFAULT_SEED=12345
```

The same request and seed produce the same candles. The generator does not use unseeded randomness.

## Settings

```txt
SYNTHETIC_FIXTURES_API_ENABLED=false
SYNTHETIC_FIXTURES_DEFAULT_SEED=12345
```

The API is disabled by default and is rejected when `APP_ENV=production`.

## API

```txt
POST /synthetic-fixtures/generate
```

Example request:

```json
{
  "pattern": "bullish_breakout",
  "symbol": "EURUSD",
  "timeframe": "1m",
  "startTime": "2026-01-01T00:00:00Z",
  "candleCount": 20,
  "startPrice": "1.1000",
  "volatility": "0.0005",
  "seed": 12345,
  "volumeBehavior": "trend",
  "outputFormat": "full"
}
```

Response includes:

- `candles`: list of candle dictionaries compatible with `RawCandlePayload`;
- `csvText`: optional CSV export when requested;
- `jsonImportPayload`: optional `/imports/candles/json` payload when workspace/source/symbol IDs are supplied;
- `metadata`: seed, requested/generated counts, missing timestamps, malformed indices, and safety flags.

JSON import payload output requires:

```txt
workspaceId
sourceId
symbolId
```

`userId` is optional.

## CLI

The CLI does not require a database and writes only to stdout:

```sh
python -m app.cli synthetic-fixtures generate \
  --pattern bullish_breakout \
  --symbol EURUSD \
  --timeframe 1m \
  --candle-count 20 \
  --output-format csv
```

JSON import payload example:

```sh
python -m app.cli synthetic-fixtures generate \
  --pattern missing_candle_gap \
  --output-format json_import_payload \
  --workspace-id 00000000-0000-0000-0000-000000000001 \
  --source-id 00000000-0000-0000-0000-000000000002 \
  --symbol-id 00000000-0000-0000-0000-000000000003
```

## Future Golden Tests

Future tests can call `SyntheticFixtureGenerator(...).generate(...)` directly and persist selected CSV outputs under `apps/api/app/tests/golden/fixtures/` only when the expected classification contract is intentionally updated.

The generator is reusable fixture code. It does not replace curated golden fixture expectations.

## Safety Boundaries

- Backend-only.
- No broker execution.
- No auto-trading.
- No financial advice.
- No UI.
- No alerts.
- No external data.
- Does not mutate production data.
- No database tables.
- Development/testing fixture generation only.
