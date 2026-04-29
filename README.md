# AI Trading Intelligence Agent

[![API CI](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml/badge.svg)](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-D71F00)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063)
![Code Style](https://img.shields.io/badge/code%20style-ruff-46A5E5)
![Type Checked](https://img.shields.io/badge/type%20checked-mypy-2A6DB2)
![Status](https://img.shields.io/badge/status-active%20backend%20foundation-blue)

Production-grade FastAPI backend for deterministic market intelligence. The system ingests historical and live OHLC candle data, validates and stores normalized market data, runs deterministic analysis engines, persists auditable artifacts, and exposes APIs for future UI and automation layers.

This repository is intentionally backend-first. It is not a trading bot, broker integration, copy-trading tool, or financial-advice system.

## Tags

`fastapi` `python` `postgresql` `neon` `sqlalchemy` `alembic` `pydantic` `market-data` `ohlc` `candlesticks` `technical-analysis` `trading-intelligence` `deterministic-analysis` `auditability` `backend-api`

## Table Of Contents

- [Product Boundary](#product-boundary)
- [Current Capabilities](#current-capabilities)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Database Migrations](#database-migrations)
- [Running The API](#running-the-api)
- [API Surface](#api-surface)
- [Analysis Pipeline](#analysis-pipeline)
- [Quality Gates](#quality-gates)
- [Docker](#docker)
- [Production Readiness](#production-readiness)
- [Security And Compliance](#security-and-compliance)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Product Boundary

The project is a market intelligence backend that turns structured market data into structured analysis.

It does:

- Parse CSV and JSON OHLC market data.
- Accept live feed ingestion events through provider adapters.
- Normalize historical and live candles through one shared validation path.
- Store clean candle data in PostgreSQL.
- Track final and partial candle state.
- Run analysis lifecycle preflight checks before generating artifacts.
- Persist deterministic feature snapshots.
- Persist deterministic indicator snapshots for EMA, RSI, MACD, and ATR.
- Store audit logs for analysis runs.
- Expose typed APIs for future UI, scanner, replay, and explanation layers.

It does not:

- Execute trades.
- Connect to brokers for order placement.
- Produce guaranteed buy or sell instructions.
- Replace regulated financial advice.
- Let an LLM classify market signals or override deterministic engines.
- Provide a frontend UI in the current phase.

Core rule:

```txt
Neon stores the truth. FastAPI controls the workflow. Deterministic engines calculate and classify. AI only explains supplied evidence.
```

## Current Capabilities

- FastAPI application factory with health routes, request IDs, structured error handling, and startup/shutdown logging.
- Pydantic v2 settings with environment-based configuration.
- Async SQLAlchemy 2.x database layer using asyncpg.
- Alembic migrations for the backend schema.
- Symbol and data-source configuration services.
- Historical CSV and JSON import pipeline.
- Shared candle normalization, validation, storage, and quality reporting.
- Live feed ingestion foundation with provider adapters, subscription lifecycle APIs, event audit persistence, stale checks, and shared candle storage.
- Candle query, count, latest, and quality APIs.
- Analysis run lifecycle for historical and live-window runs.
- Deterministic feature engineering snapshots.
- Deterministic indicator snapshots.
- Pytest, Ruff, mypy, and GitHub Actions CI.

## Architecture

```txt
Client or Worker
      |
      v
FastAPI Routes
      |
      v
Service Layer
      |
      v
Repositories
      |
      v
Neon PostgreSQL
      |
      v
Deterministic Analysis Engines
      |
      v
Persisted Artifacts + Audit Logs
```

Data ingestion converges through the same candle boundary:

```txt
CSV / JSON imports
Live feed messages
Future API polling
Manual seed data
        |
        v
NormalizedCandleInput
        |
        v
Candle validation
        |
        v
Candle repository upsert rules
        |
        v
Analysis lifecycle
```

Final candles are the default source for analysis. Partial candles are stored and can be inspected, but analysis includes them only when explicitly requested by the calling workflow.

## Repository Layout

```txt
.
+-- AGENTS.md
+-- README.md
+-- apps/
|   +-- api/
|       +-- app/
|       |   +-- core/
|       |   +-- db/
|       |   +-- modules/
|       |   +-- routes/
|       |   +-- tests/
|       |   +-- config.py
|       |   +-- dependencies.py
|       |   +-- main.py
|       +-- alembic/
|       +-- docs/
|       +-- Dockerfile
|       +-- README.md
|       +-- alembic.ini
|       +-- pyproject.toml
+-- docs/
|   +-- backend-only-implementation-plan.md
|   +-- backend-phase-0-architecture-plan.md
|   +-- project-state.md
+-- .github/
    +-- workflows/
        +-- api-ci.yml
```

## Technology Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI |
| Runtime | Python 3.12+ |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| Database | Neon PostgreSQL |
| ORM | SQLAlchemy 2.x async |
| Driver | asyncpg |
| Migrations | Alembic |
| Testing | pytest, pytest-asyncio, httpx |
| Linting | Ruff |
| Type checking | mypy strict mode |
| CI | GitHub Actions |
| Container | Docker |

## Quick Start

From the repository root:

```sh
cd apps/api
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
cp .env.example .env
```

Set `DATABASE_URL` in `apps/api/.env` before running migrations or database-backed routes.

```sh
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

The API will be available at:

```txt
http://127.0.0.1:8000
```

Interactive OpenAPI docs:

```txt
http://127.0.0.1:8000/docs
```

Health check:

```sh
curl http://127.0.0.1:8000/health
```

Database health check:

```sh
curl http://127.0.0.1:8000/health/db
```

## Configuration

Configuration is read from environment variables and `apps/api/.env`.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `APP_ENV` | No | `development` | Runtime environment: `development`, `test`, `staging`, or `production`. |
| `API_PREFIX` | No | empty | Optional API path prefix. Must be empty or start with `/`. |
| `LOG_LEVEL` | No | `INFO` | Logging level. |
| `DATABASE_URL` | For DB features | empty | PostgreSQL or Neon connection string. `postgresql://` and `postgres://` are normalized to asyncpg. |
| `TEST_DATABASE_URL` | For DB tests/smoke | empty | Explicit disposable database target for integration tests and smoke checks. |
| `REDIS_URL` | Future workers | empty | Reserved for background processing and cache-backed workflows. |
| `OPENAI_API_KEY` | Future explanation layer | empty | Reserved for explanation-only AI workflows. |
| `CORS_ALLOWED_ORIGINS` | No | empty | Comma-separated allowed browser origins. Do not use `*` in production. |
| `CORS_ALLOW_CREDENTIALS` | No | `false` | Enables credentialed CORS responses for configured origins. |
| `AUTH_ENABLED` | No | `false` | Enables API key protection for mutating routes. |
| `ADMIN_API_KEY` | When auth enabled | empty | API key used with `API_KEY_HEADER_NAME`; never commit a real value. |
| `API_KEY_HEADER_NAME` | No | `x-admin-api-key` | Header read by the optional API key guard. |
| `RATE_LIMIT_ENABLED` | No | `false` | Enables lightweight write-route rate limiting. |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | `60` | Per-client, per-route write limit when enabled. |
| `MAX_REQUEST_BODY_BYTES` | No | `1048576` | Maximum non-upload request body size. |
| `MAX_UPLOAD_FILE_BYTES` | No | `10485760` | Maximum multipart upload size. |
| `LIVE_FEED_PROVIDER` | For live ingestion | empty | Optional live market data provider selector. |
| `LIVE_FEED_API_KEY` | Provider dependent | empty | Optional provider credential. Keep out of Git. |

Do not commit `.env`, credentials, tokens, private keys, API keys, sample secrets, or customer market data.

## Database Migrations

Run migrations from `apps/api`:

```sh
.venv/bin/alembic upgrade head
```

Inspect migration history:

```sh
.venv/bin/alembic history
```

Create a new migration only after the SQLAlchemy models and schema intent are clear:

```sh
.venv/bin/alembic revision -m "describe_change"
```

## Running The API

Development:

```sh
cd apps/api
.venv/bin/uvicorn app.main:app --reload
```

Production-style local run:

```sh
cd apps/api
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Surface

All routes are mounted under `API_PREFIX` when configured.

| Area | Routes |
| --- | --- |
| Health | `GET /health`, `GET /health/db` |
| Symbols | `POST /symbols`, `GET /symbols`, `GET /symbols/{symbol_id}`, `PATCH /symbols/{symbol_id}` |
| Data sources | `POST /data-sources`, `GET /data-sources`, `GET /data-sources/{data_source_id}`, `PATCH /data-sources/{data_source_id}` |
| Imports | `POST /imports/csv`, `POST /imports/json`, `GET /imports/{import_batch_id}`, `GET /imports/{import_batch_id}/errors` |
| Live ingestion | Subscription lifecycle, stale checks, feed event ingestion, event listing |
| Candles | `GET /candles`, `GET /candles/count`, `GET /candles/quality`, `GET /candles/latest` |
| Analysis | Historical runs, live-window runs, run listing, run details, audit logs, features, indicators, retry |

Use `/docs` or `/openapi.json` from a running server for exact request and response schemas.

## Analysis Pipeline

Current implemented lifecycle:

```txt
Create analysis run
      |
      v
Resolve workspace, symbol, source, timeframe, and candle window
      |
      v
Preflight final-candle sufficiency
      |
      v
Persist audit logs
      |
      v
Persist feature snapshot
      |
      v
Persist indicator snapshot
      |
      v
Mark run completed or insufficient_data
```

Current deterministic artifacts:

- Movement metrics.
- Candle shape metrics.
- Range metrics.
- Volatility metrics.
- Trend metrics.
- EMA 9, EMA 21, EMA 50.
- RSI 14.
- MACD.
- ATR 14.
- Readiness metadata for indicators with insufficient warmup data.

Decimal market values are serialized as strings in JSON artifacts to preserve precision.

## Quality Gates

Run from `apps/api`:

```sh
.venv/bin/ruff check .
.venv/bin/mypy app
.venv/bin/pytest
```

Repository-level whitespace check:

```sh
git diff --check
```

CI runs Ruff, mypy, and pytest for API changes through `.github/workflows/api-ci.yml`.

## Docker

Build the API image:

```sh
cd apps/api
docker build -t trading-intelligence-api .
```

Run the container:

```sh
docker run --rm -p 8000:8000 --env-file .env trading-intelligence-api
```

## Production Readiness

Before a production deployment, verify:

- `APP_ENV=production`.
- `DATABASE_URL` points to the intended Neon database.
- Alembic migrations are applied.
- Secrets are injected by the deployment platform, not committed.
- `/health` returns healthy.
- `/health/db` returns healthy.
- CI is passing on the deployed commit.
- Logs are collected centrally.
- Database backups, retention, and restore testing are configured.
- API ingress applies TLS, rate limits, and request-size limits.
- Provider credentials are scoped and rotated.
- Market-data provider terms are satisfied.
- No endpoint implies guaranteed trading outcomes or regulated financial advice.

## Security And Compliance

- Secrets are represented with `SecretStr` in settings and must stay out of source control.
- The current product scope avoids trade execution and broker order placement.
- Deterministic engines produce analysis artifacts; LLMs may only explain supplied evidence in future phases.
- Persisted artifacts support audit and replay.
- Request IDs are attached to API responses for traceability.
- Financial outputs should be framed as informational analysis, not investment advice.

## Documentation

Durable project documentation:

- [Backend-only implementation plan](docs/backend-only-implementation-plan.md)
- [Phase 0 backend architecture plan](docs/backend-phase-0-architecture-plan.md)
- [Project state](docs/project-state.md)

API-specific documentation:

- [API README](apps/api/README.md)
- [Core schema](apps/api/docs/schema/core-schema.md)
- [Configuration services](apps/api/docs/configuration-services.md)
- [Candle normalization](apps/api/docs/candle-normalization.md)
- [Historical imports](apps/api/docs/historical-imports.md)
- [Live feed ingestion](apps/api/docs/live-feed-ingestion.md)
- [Candle query and quality](apps/api/docs/candle-query-quality.md)
- [Analysis run lifecycle](apps/api/docs/analysis-run-lifecycle.md)
- [Feature engineering](apps/api/docs/feature-engineering.md)
- [Indicator engine](apps/api/docs/indicator-engine.md)

## Roadmap

Implemented:

- Backend foundation.
- Core database schema.
- Symbol and data-source configuration.
- Historical import pipeline.
- Live feed ingestion foundation.
- Candle query and quality APIs.
- Analysis run lifecycle.
- Feature snapshots.
- Indicator snapshots.

Planned:

- Pattern candidates.
- Core intelligence layer: deterministic strategy profiles, signal classification, evidence, confidence, risk notes, and deterministic explanations.
- Golden dataset tests for intelligence quality.
- Explanation layer constrained to supplied evidence.
- Replay and versioning.
- News and event correlation.
- Live scanning.
- Background workers.
- Observability, security hardening, and performance tuning.
- Future frontend UI.

Out of scope for the current backend phase:

- Broker execution.
- Auto-trading.
- Copy trading.
- Social trading.
- Guaranteed trade recommendations.

## Contributing

Use the established backend conventions:

- Keep modules small and service-oriented.
- Use typed Pydantic schemas at API boundaries.
- Use repositories for database access.
- Route historical and live candle data through shared normalization.
- Prefer deterministic engines for analysis and classification.
- Add or update migrations with schema changes.
- Run Ruff, mypy, pytest, and `git diff --check` before pushing.
- Keep commit messages under 140 characters.

## License

No license file is currently published for this repository. Add a license before distributing, packaging, or accepting external contributions.
