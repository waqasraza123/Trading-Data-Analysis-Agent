# Trading Intelligence API

FastAPI backend for deterministic market intelligence over imported and live-originated
candle data. The backend stores market data, calculates features and indicators, classifies
signals with rules, generates safe deterministic explanations from persisted artifacts, and
supports replay from stored candles.

No UI, LLM calls, news/event correlation, broker execution, auto-trading, alerts, or billing
is implemented in this backend slice.

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
symbols, default workspace data sources, strategy profiles, and current engine versions.
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

Run lint:

```sh
.venv/bin/ruff check .
```

Run typecheck:

```sh
.venv/bin/mypy app
```

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
