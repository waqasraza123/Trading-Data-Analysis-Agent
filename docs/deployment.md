# Deployment

This project now has production-oriented Docker images for the FastAPI API and Next.js web app.
Production secrets must be injected by the deployment platform, never baked into images.

## API Image

Build from the repository root:

```sh
docker build -f apps/api/Dockerfile -t trading-intelligence-api:latest .
```

The API image:

- Uses a multi-stage Python 3.12 build.
- Installs only runtime dependencies from `apps/api/pyproject.toml`.
- Runs as a non-root user.
- Copies only the API package, Alembic migrations, and Alembic config into the final image.
- Exposes port `8000`.
- Uses `/health/live` for a liveness healthcheck.

Required production environment:

```txt
APP_ENV=production
DATABASE_URL=postgresql://...
CORS_ALLOWED_ORIGINS=https://your-web-origin.example
AUTH_ENABLED=true
ADMIN_API_KEY=provided-by-secret-manager
```

Optional production environment:

```txt
REDIS_URL=redis://...
RATE_LIMIT_ENABLED=true
WORKER_SUPERVISOR_COMPONENTS=reasoning_actions,notifications,market_scans
```

Run migrations before serving traffic:

```sh
docker run --rm --env-file apps/api/.env trading-intelligence-api:latest alembic upgrade head
```

## Web Image

Build from the repository root:

```sh
docker build \
  -f apps/web/Dockerfile \
  --build-arg NEXT_PUBLIC_API_BASE_URL=https://your-api-origin.example \
  --build-arg NEXT_PUBLIC_APP_NAME="Daily Trading Dashboard" \
  -t trading-intelligence-web:latest .
```

The web image:

- Uses `npm ci` with the committed lockfile.
- Builds Next.js standalone output.
- Runs as the non-root `node` user.
- Exposes port `3000`.

`NEXT_PUBLIC_API_BASE_URL` is public frontend configuration. Do not put secrets in
`NEXT_PUBLIC_*` variables.

## Local Production-Like Stack

```sh
make docker-up
```

This starts PostgreSQL, Redis, API, and web with local development-safe credentials. It is not a
production secrets model.

## CI

`.github/workflows/ci.yml` has three jobs:

- `backend`: installs API dev dependencies, runs Ruff, mypy, pytest, and Alembic heads/history.
- `frontend`: installs with `npm ci`, then runs lint, typecheck, and build with mocked public env.
- `docker`: builds API and web production images.

Integration tests are intentionally excluded from default CI. Run them only when
`TEST_DATABASE_URL` points at a disposable database.

## Worker Deployment

The API image can run worker entrypoints by changing the command:

```sh
python -m app.workers.live_feed_worker
python -m app.workers.market_scan_worker
python -m app.workers.supervisor
```

Use separate processes or services for API and workers. Keep worker environment separate from web
public environment. Do not enable provider polling, notification delivery, or LLM providers without
explicit production secrets and operational review.
