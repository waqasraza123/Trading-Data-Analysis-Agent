# Phase 0 Backend Architecture Plan

## Current Repo State

- Repository has no committed history on local `main`.
- Existing files are documentation only: `AGENTS.md`, `.gitignore`, `docs/project-state.md`, `docs/backend-only-implementation-plan.md`, and ignored local session memory.
- No FastAPI app exists.
- No Python package metadata exists.
- No database, migration, test, lint, typecheck, Docker, CI, or environment configuration exists.
- No frontend exists.

## Existing Backend Structure

None. There is no backend implementation to extend.

## Recommended Backend Folder Structure

Create a new backend under `apps/api/`:

```txt
apps/api/
  app/
    main.py
    config.py
    dependencies.py
    db/
      base.py
      session.py
      migrations/
    core/
      errors.py
      logging.py
      pagination.py
      security.py
      time.py
    modules/
      symbols/
      data_sources/
      imports/
      candles/
      live/
      analysis/
      features/
      indicators/
      patterns/
      signals/
      explanations/
      news/
      engine_versions/
      audit/
    workers/
    tests/
      unit/
      integration/
      golden/
```

Keep API routes thin. Business rules belong in services and deterministic engines. Repositories own database access.

## Database / Migration Approach

- Use Neon PostgreSQL as the source of truth.
- Use SQLAlchemy 2.x async ORM with `asyncpg`.
- Use Alembic for migrations under `apps/api/app/db/migrations/`.
- Keep model metadata centralized in `app/db/base.py`.
- Phase 1 creates migration infrastructure only.
- Phase 2 creates the first schema: workspaces, users, symbols, data_sources, import_batches, import_errors, candles, live_feed_subscriptions, live_feed_events, analysis_runs, analysis_audit_logs, and engine_versions.

The `candles` table must be the normalized truth table for both imported historical candles and live feed candles. `import_batch_id` tracks CSV/JSON imports. `live_feed_event_id` tracks live-originated candles. `is_final` separates partial live candles from final candles.

## Worker Approach

- Use Redis as the queue/broker dependency.
- Start with a worker abstraction in `apps/api/app/workers/`.
- Prefer Dramatiq for the first implementation because it is small, typed-friendly, and sufficient for import jobs, analysis runs, live event processing, and scheduled scanning.
- Keep job payloads ID-based so workers reload state from Neon rather than trusting request payloads.
- Make jobs idempotent: imports, live events, live scans, and analysis retries must be safe to re-run.

## Testing Approach

- Use pytest.
- Use pytest-asyncio for async service/repository tests.
- Use httpx ASGI transport for FastAPI route tests.
- Use unit tests for validation, normalization, feature engines, indicators, patterns, signal classification, confidence, and explanation safety.
- Use integration tests for database repositories and migrations.
- Use golden tests for imported CSV and live feed event datasets.
- Phase 1 must include basic app, config, health, and error-handler tests.

## Environment Variable Pattern

Use Pydantic v2 settings with environment variables:

```txt
DATABASE_URL
APP_ENV
API_PREFIX
LOG_LEVEL
REDIS_URL
OPENAI_API_KEY
LIVE_FEED_PROVIDER
LIVE_FEED_API_KEY
```

Optional provider keys must not be required at startup unless the corresponding feature is enabled.

## Deployment Assumptions

- Backend runs as a Python 3.12+ FastAPI service.
- Database is Neon PostgreSQL.
- Redis is available for workers once background jobs are enabled.
- App process and worker process should be independently runnable.
- No frontend deployment is in scope yet.

## Module Boundaries

- `imports`: CSV/JSON batch intake and import audit trail.
- `live`: provider adapters, subscriptions, raw live event audit, stale detection, reconnect behavior.
- `candles`: shared validation, normalization, upsert, querying, and quality checks for both import and live paths.
- `analysis`: analysis lifecycle, status transitions, audit logs, orchestration.
- `features`, `indicators`, `patterns`, `signals`: deterministic calculation and classification only.
- `explanations`: deterministic explanation first, optional LLM explanation second.
- `news`: later event ingestion and cautious correlation.

## Non-Negotiable Implementation Rules

- CSV and live feed inputs must normalize into the same candle table.
- The analysis engine must not care whether candles came from CSV, JSON, API polling, or live websocket events.
- Analysis must use final candles by default.
- Partial live candles may be included only when explicitly requested.
- LLMs must never classify market direction or override deterministic output.
- Every signal must store evidence and confidence components.
- Every analysis run must be auditable and reproducible.
- No frontend, broker execution, auto-trading, or financial-advice output.

## Risks Before Implementation

- No current package manager exists, so Phase 1 will set long-lived Python tooling conventions.
- No real Neon URL is present; DB health and migration tests need environment-gated behavior or a local/test database fallback.
- Live feed support adds idempotency and partial/final candle complexity that must be designed into the schema from Phase 2.
- Financial-domain wording must stay cautious and must not imply certainty about market outcomes or trading advice.
- First implementation choices will define repository conventions because the repo is otherwise empty.

## Phase 1 Files To Create / Change

```txt
apps/api/app/main.py
apps/api/app/config.py
apps/api/app/dependencies.py
apps/api/app/db/base.py
apps/api/app/db/session.py
apps/api/app/core/errors.py
apps/api/app/core/logging.py
apps/api/app/core/pagination.py
apps/api/app/core/security.py
apps/api/app/core/time.py
apps/api/app/tests/unit/test_config.py
apps/api/app/tests/unit/test_health.py
apps/api/app/tests/unit/test_errors.py
apps/api/pyproject.toml
apps/api/alembic.ini
apps/api/app/db/migrations/env.py
apps/api/app/db/migrations/script.py.mako
apps/api/Dockerfile
apps/api/.env.example
.github/workflows/api-ci.yml
docs/project-state.md
docs/_local/current-session.md
```

## Phase 1 Acceptance Criteria

- FastAPI app starts locally.
- `GET /health` returns service health.
- `GET /health/db` checks database connectivity when `DATABASE_URL` is configured.
- Settings load from environment and do not require optional feature keys at startup.
- Async SQLAlchemy session factory is configured.
- Alembic migration environment loads application metadata.
- Global exception handlers return structured JSON with request IDs.
- Tests run with pytest.
- Ruff lint and typecheck commands exist and pass.
- No trading intelligence business logic is implemented yet.
