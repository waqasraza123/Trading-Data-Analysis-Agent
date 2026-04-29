# Disposable Database Validation

The integration suite validates the backend against a real PostgreSQL or Neon-compatible
database. Use a disposable database only.

## Safety Rules

- Integration tests require `TEST_DATABASE_URL`.
- Without `TEST_DATABASE_URL`, integration tests skip cleanly and unit tests still run.
- Do not set `TEST_DATABASE_URL` to production Neon.
- If `TEST_DATABASE_URL` equals `DATABASE_URL` and `APP_ENV` or `ENV` is `prod` or
  `production`, pytest refuses to run integration tests.
- The smoke command also refuses `TEST_DATABASE_URL` when it equals `DATABASE_URL` under a
  production-like `APP_ENV` or `ENV`.
- The integration fixture migrates the test database to Alembic head and truncates app tables
  before and after the session.

## Migrations

```sh
cd apps/api
DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/alembic upgrade head
```

The validation suite also checks that Alembic has one head, the disposable database is at head,
and critical backend tables exist.

## Integration Tests

```sh
cd apps/api
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/pytest -m integration
```

Run the full unit plus integration selection:

```sh
cd apps/api
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/pytest
```

Run unit tests without database credentials:

```sh
cd apps/api
.venv/bin/pytest
```

Expected no-DB behavior is passed unit tests plus skipped integration tests.

## Seed Idempotency

```sh
cd apps/api
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli seed
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli seed
```

The seed integration tests verify no duplicate default symbols, data sources, strategy profiles,
or engine versions are created by a second seed run.

## Smoke Command

Read-only smoke:

```sh
cd apps/api
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli smoke
```

Explicit write smoke:

```sh
cd apps/api
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli smoke --include-write-tests
```

Select a different configured URL environment variable:

```sh
cd apps/api
DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli smoke --database-url-env DATABASE_URL
```

The default smoke command does not mutate data. Write checks require `--include-write-tests` and
are refused when `APP_ENV` or `ENV` is production-like. If auth is enabled, API-level smoke tests
use the configured API key header; health and liveness endpoints remain public.

## Smoke Coverage

The disposable DB suite covers:

- Alembic migration/head validation.
- Seed idempotency.
- Workspace and user API smoke.
- Symbol, data source, strategy profile, and engine-version default seed smoke.
- CSV and JSON candle ingestion.
- Mock live partial/final candle ingestion.
- Historical and live-window analysis lifecycle output.
- Signal classification artifacts, deterministic explanations, and audit logs.
- Latest-engine and same-engine replay, including original artifact immutability.
