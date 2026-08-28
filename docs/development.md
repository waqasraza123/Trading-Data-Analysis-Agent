# Development Setup

This repository uses two package managers:

- API: Python packaging from `apps/api/pyproject.toml`.
- Web: npm from `apps/web/package.json` and `apps/web/package-lock.json`.

Do not switch package managers unless the repository metadata changes.

## One-Command Docker Dev

Start PostgreSQL, Redis, the FastAPI reload server, and the Next.js reload server:

```sh
make dev
```

Open:

```txt
http://127.0.0.1:8000/health
http://127.0.0.1:3000
http://127.0.0.1:3000/command-center
```

The dev compose stack uses:

```txt
DATABASE_URL=postgresql://trading:trading@postgres:5432/trading_intelligence
REDIS_URL=redis://redis:6379/0
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

Apply migrations after the database is healthy:

```sh
make migrate
```

Seed deterministic defaults when needed:

```sh
make seed
```

## Local API Without Docker

```sh
./scripts/dev-api.sh
```

The script creates `apps/api/.venv`, installs `.[dev]`, copies `.env.example` to `.env` when
missing, and starts Uvicorn with reload.

Run API checks:

```sh
make api-check
```

Integration tests require an explicit disposable database:

```sh
cd apps/api
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/pytest -m integration
```

Do not point `TEST_DATABASE_URL` at production data.

## Local Web Without Docker

```sh
./scripts/dev-web.sh
```

The script installs with `npm ci` when `package-lock.json` exists and starts the Next.js dev server.

Run web checks:

```sh
make web-check
```

Only `NEXT_PUBLIC_*` values belong in `apps/web/.env.local`. Backend secrets stay in API or
deployment environment configuration.

## Workers

Run the configured supervisor locally:

```sh
./scripts/run-workers.sh
```

Docker worker examples are profile-gated:

```sh
docker compose --profile workers up --build live-worker market-scan-worker job-queue-worker
```

Worker services require a migrated database and only run the existing backend worker entrypoints.
They do not execute broker workflows, auto-trading, or external provider calls unless the relevant
backend settings explicitly enable those behaviors.

## Reproducibility Notes

- The web app has a committed `package-lock.json`; use `npm ci` for clean installs.
- The API currently has no Python lockfile; `pyproject.toml` is the source of truth.
- The production API image installs runtime dependencies only, without `.[dev]`.
- The production web image uses Next.js standalone output.
- `.env.example` files are templates only and must not contain secrets.
