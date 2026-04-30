# Trading Intelligence API

FastAPI backend for deterministic market intelligence over imported and live-originated
candle data. The backend stores market data, calculates features and indicators, classifies
signals with rules, generates safe deterministic and optional grounded LLM explanations from
persisted artifacts, supports replay from stored candles, and persists deterministic news/event
context for analysis-aware workflows. It also accepts manually or externally extracted trading
chart screenshot candles and persists deterministic next-trend hypotheses.

No UI, broker execution, auto-trading, alerts, or billing is implemented in this backend slice.
The LLM explanation layer is optional and may only explain persisted deterministic output.

## Commands

Install dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the development server:

```sh
.venv/bin/uvicorn app.main:app --reload
```

Run migrations:

```sh
.venv/bin/alembic upgrade head
```

Seed deterministic backend defaults:

```sh
SEED_DEFAULT_WORKSPACE_NAME="Default Workspace" \
SEED_DEFAULT_ADMIN_EMAIL="admin@example.test" \
SEED_DEFAULT_ADMIN_NAME="Default Admin" \
.venv/bin/python -m app.cli seed
```

The seed command is idempotent. It seeds configured workspace/admin user defaults, default
symbols, default workspace data sources including manual news context, strategy profiles,
and current engine versions.
`SEED_DEFAULT_WORKSPACE_NAME`, `SEED_DEFAULT_ADMIN_EMAIL`, and `SEED_DEFAULT_ADMIN_NAME`
are optional; data sources and the admin user are seeded only when a default workspace is
configured.

Run tests:

```sh
.venv/bin/pytest
```

Run database integration tests against an explicit disposable database:

```sh
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/pytest -m integration
```

If `TEST_DATABASE_URL` is not set, integration tests are skipped and unit tests still run.
Do not point `TEST_DATABASE_URL` at production data. If `TEST_DATABASE_URL` equals
`DATABASE_URL` while `APP_ENV` or `ENV` is production-like, the integration suite refuses to run.

Run migrations against a disposable database:

```sh
DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/alembic upgrade head
```

Seed deterministic defaults against a disposable database:

```sh
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli seed
```

Run the read-only backend smoke command:

```sh
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli smoke
```

Run smoke write checks only against a disposable database:

```sh
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli smoke --include-write-tests
```

Run lint:

```sh
.venv/bin/ruff check .
```

Run typecheck:

```sh
.venv/bin/mypy app
```

## Operations

Health and readiness endpoints:

```txt
GET /health
GET /health/live
GET /health/db
GET /health/ready
GET /health/workers
```

`/health` and `/health/live` only prove the API process is alive. `/health/db` checks
database connectivity. `/health/ready` requires database connectivity and valid critical
configuration. `/health/workers` reports live worker and stale monitor state when a database is
configured, and returns a safe degraded status otherwise.

Run the live feed worker:

```sh
.venv/bin/python -m app.workers.live_feed_worker
```

Run the stale monitor:

```sh
.venv/bin/python -m app.workers.live_stale_monitor
```

Security and traffic controls are configured through environment variables:

```txt
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=false
AUTH_ENABLED=false
ADMIN_API_KEY=
API_KEY_HEADER_NAME=x-admin-api-key
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60
MAX_REQUEST_BODY_BYTES=1048576
MAX_UPLOAD_FILE_BYTES=10485760
```

`AUTH_ENABLED=false` is the local/test default. When enabled, mutating routes require the
configured API key header; health/readiness endpoints stay public. Rate limiting is disabled by
default and currently uses an in-memory local/test foundation unless a production Redis-backed
implementation is added later.

Logs are JSON records with request id, method, path, status code, duration, safe client host, and
error code when applicable. Request bodies, uploaded files, tokens, API keys, database URLs, and
live feed keys are not logged.

## Schema Docs

The Phase 2 core schema is documented in:

```txt
docs/schema/core-schema.md
```

The Phase 3 configuration services are documented in:

```txt
docs/configuration-services.md
```

The shared candle validation and normalization layer is documented in:

```txt
docs/candle-normalization.md
```

Historical CSV and JSON import wiring is documented in:

```txt
docs/historical-imports.md
```

Live feed ingestion foundation is documented in:

```txt
docs/live-feed-ingestion.md
```

Operational hardening is documented in:

```txt
docs/operations.md
docs/security.md
docs/live-runtime.md
```

Candle query and quality APIs are documented in:

```txt
docs/candle-query-quality.md
```

Analysis run lifecycle is documented in:

```txt
docs/analysis-run-lifecycle.md
```

Feature engineering snapshots are documented in:

```txt
docs/feature-engineering.md
```

Indicator snapshots are documented in:

```txt
docs/indicator-engine.md
```

Pattern candidates are documented in:

```txt
docs/pattern-engine.md
```

Deterministic signal classification is documented in:

```txt
docs/signal-classification.md
```

Deterministic explanations are documented in:

```txt
docs/deterministic-explanations.md
```

Deterministic news/event correlation is documented in:

```txt
docs/news-event-correlation.md
```

Chart screenshot trend prediction is documented in:

```txt
docs/chart-screenshot-prediction.md
```

Grounded LLM explanations are documented in:

```txt
docs/llm-explanations.md
```

When both `includeNewsCorrelation` and `includeAiExplanation` are enabled, news correlation runs
before LLM explanation generation so the LLM can only use persisted correlation context.

Workspace/user APIs expose backend setup primitives:

```txt
POST /workspaces
GET /workspaces
GET /workspaces/{workspace_id}
PATCH /workspaces/{workspace_id}
POST /users
GET /users
GET /users/{user_id}
PATCH /users/{user_id}
```

Engine versions are queryable through:

```txt
GET /engine-versions
GET /engine-versions/{engine_name}
POST /engine-versions/seed
```

Replay supports `latest_engine_version` and `same_engine_version`. Same-version replay is
supported for the currently registered v1 deterministic engines and returns
`unsupported_engine_version` instead of falling back when a stored snapshot references an
unregistered engine version.

Chart screenshot APIs support manually or externally extracted OHLC rows and deterministic PNG
candlestick extraction from trading chart images. Valid extracted rows are stored through the shared
candle path and persisted with a deterministic next-trend hypothesis. Both create endpoints can
optionally trigger the existing deterministic analysis lifecycle after extraction. PNG preview and
image ingestion support request-scoped parser tuning for chart bounds, candle colors, foreground
thresholds, and cluster detection:

```txt
POST /chart-screenshot-runs
POST /chart-screenshot-runs/image/preview
POST /chart-screenshot-runs/image
GET /chart-screenshot-runs
GET /chart-screenshot-runs/{run_id}
POST /chart-screenshot-runs/{run_id}/review
GET /chart-screenshot-runs/{run_id}/decision
GET /chart-screenshot-runs/{run_id}/report
```

Disposable database validation, integration fixtures, and smoke commands are documented in:

```txt
docs/integration-tests.md
```
