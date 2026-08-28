# AI Trading SaaS Starter Kit

[![CI](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/ci.yml/badge.svg)](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/ci.yml)
[![API CI](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml/badge.svg)](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml)
[![Web CI](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/web-ci.yml/badge.svg)](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/web-ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e.svg)](LICENSE)
![Next.js](https://img.shields.io/badge/Next.js_15-React_19-111827?logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Python_3.12-05998b?logo=fastapi)
![Neon](https://img.shields.io/badge/Neon-Postgres-00e599?logo=postgresql)
![Go](https://img.shields.io/badge/Go-market_worker-00add8?logo=go)
![Safety](https://img.shields.io/badge/safety-no_broker_execution-2563eb)

An open-source, production-minded starter kit for building explainable AI trading intelligence products with Next.js, FastAPI, Neon Postgres, and Go.

It includes market-data ingestion, deterministic analysis, grounded AI explanations, workspace authentication, paper-only agent plans, review workflows, background jobs, and an operator cockpit. It does not place orders, connect to brokers for execution, or present model output as financial advice.

[Live site](https://ai-trading-agent-seven.vercel.app) · [Use this template](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/generate) · [Development guide](docs/development.md) · [Deployment guide](docs/deployment.md)

![AI Trading SaaS Starter Kit landing page](docs/assets/ai-trading-saas-starter-kit.png)

## Why this starter kit

Most SaaS starters stop at billing, authentication, and an empty dashboard. This repository provides a complete vertical foundation for trading-intelligence products:

- Normalize imported, provider-polled, and live candle data into one auditable model.
- Run indicators, patterns, regimes, signal classification, confidence, quality gates, and outcome evaluation deterministically.
- Let AI explain or compare persisted evidence without allowing it to rewrite source signals.
- Review ranked setups, daily briefs, scans, data health, paper plans, outcomes, and journal notes in a real product UI.
- Start with Neon-backed workspace accounts, RBAC, HTTP-only sessions, queues, workers, health checks, and audit trails.
- Keep optional backend modules fail-soft so one unavailable integration does not break the cockpit.

## Included product surfaces

| Area | What is included |
| --- | --- |
| Public product | Developer landing page, starter-kit metadata, GitHub template calls to action, login, and registration |
| Daily workflow | Command center, brief, signal triage, setup review, scanner, readiness, and onboarding |
| Research | Equity universes, fundamentals, earnings, catalysts, candidates, and background data operations |
| Intelligence | Deterministic signals, evidence, scenarios, historical cases, confidence, quality, and outcomes |
| Paper agent | Human-reviewed paper plans and observations with no live-order path |
| Accounts | Neon-backed registration, login, logout, profile, password change, session inventory, revocation, and activity |
| Operations | Job queue, Python workers, Go market worker, provider health, runtime supervisor, and observability |

## Architecture

```mermaid
flowchart LR
    Browser[Next.js web] -->|HTTP-only session proxy| API[FastAPI]
    API --> Neon[(Neon Postgres)]
    API --> Redis[(Redis)]
    Python[Python workers] --> Neon
    Go[Go market worker] --> Neon
    Providers[Market data providers] --> Go
    Imports[CSV / JSON imports] --> API
    API --> Engine[Deterministic intelligence]
    Engine --> Evidence[Persisted evidence]
    Evidence --> AI[Grounded AI explanations]
```

Python owns the API, product workflows, database contracts, and deterministic intelligence. Go is an additive ingestion sidecar. Neon stores the source of truth. Redis supports distributed rate limits and queued work where configured.

Core rule:

```txt
Persisted artifacts are the source of truth. Deterministic engines classify and score. AI may only explain supplied evidence.
```

## Quick start

### 1. Create your repository

Use [this repository as a GitHub template](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/generate), or clone it directly:

```sh
git clone https://github.com/waqasraza123/Trading-Data-Analysis-Agent.git
cd Trading-Data-Analysis-Agent
```

### 2. Start the development stack

Docker is the fastest route to PostgreSQL, Redis, FastAPI, and Next.js:

```sh
make dev
```

In another terminal, apply the schema and seed deterministic defaults:

```sh
make migrate
make seed
```

Open:

```txt
http://127.0.0.1:3000
http://127.0.0.1:3000/command-center
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/health
```

Run without Docker when preferred:

```sh
./scripts/dev-api.sh
./scripts/dev-web.sh
```

## Neon and production authentication

The local stack defaults to developer mode. For a deployed first-party account flow, configure the API with a migrated Neon database:

```txt
APP_ENV=production
DATABASE_URL=postgresql://user:password@pooler-host/database?sslmode=require
AUTH_MODE=session
AUTH_PASSWORD_ENABLED=true
AUTH_PASSWORD_SIGNUP_ENABLED=true
CORS_ALLOWED_ORIGINS=https://your-web.example
```

Configure the web runtime:

```txt
NEXT_PUBLIC_API_BASE_URL=https://your-api.example
NEXT_PUBLIC_APP_NAME=AI Trading SaaS Starter Kit
NEXT_PUBLIC_SITE_URL=https://your-web.example
NEXT_PUBLIC_REPOSITORY_URL=https://github.com/your-name/your-repository
NEXT_PUBLIC_AUTH_MODE=session
WEB_API_PROXY_BASE_URL=https://your-api.example
WEB_AUTH_SESSION_COOKIE=trading_intelligence_session
```

Use a Neon pooled connection string for the application. Run Alembic migrations before enabling traffic. Never put database credentials, API keys, or provider secrets in `NEXT_PUBLIC_*` variables.

Session tokens are stored as hashes in Postgres and transported to the browser only through secure HTTP-only cookies. New passwords use Argon2id; existing PBKDF2 credentials are upgraded after a successful login.

## Customize the starter

- Set the public product name and repository/site URLs in `apps/web/.env.local`.
- Replace the landing-page copy and preview in `apps/web/src/components/marketing`.
- Configure strategy profiles, rule packs, scanner presets, and seeded symbols for your market niche.
- Enable only the providers, workers, LLM layers, and notifications your deployment needs.
- Keep broker execution separate. No order or brokerage contract exists in this starter.

## Repository layout

| Path | Role |
| --- | --- |
| `apps/api` | FastAPI, SQLAlchemy/Alembic, auth/RBAC, intelligence modules, workers, and backend docs |
| `apps/web` | Next.js App Router product, public landing page, auth boundary, cockpit, and Playwright tests |
| `apps/go/market-worker` | Bounded market-data polling/live ingestion sidecar and health endpoints |
| `docs` | Development, deployment, architecture, project state, and operating guidance |

## Quality checks

```sh
make api-check
make web-check
git diff --check
```

Focused commands:

```sh
cd apps/api && ruff check app alembic && pytest
cd apps/web && npm run typecheck && npm run lint && npm run build
cd apps/web && npm run test:e2e
cd apps/go/market-worker && go test ./...
```

Database integration tests require an explicit disposable `TEST_DATABASE_URL`. They refuse production-like database reuse. Some provider and LLM tests require separately configured credentials.

## Safety boundary

The starter kit can ingest market data, persist deterministic intelligence, compose grounded explanations, create paper-only plans, and record observations. It intentionally does not:

- place orders or connect to brokers for execution;
- auto-trade, copy-trade, or create direct order instructions;
- treat observed outcomes as account P&L or broker performance;
- let an LLM mutate source signals or override deterministic classification;
- store raw provider secrets in source, queued payloads, or API responses;
- provide regulated financial advice.

## Documentation

- [Development setup](docs/development.md)
- [Deployment](docs/deployment.md)
- [API guide](apps/api/README.md)
- [Web guide](apps/web/README.md)
- [Authentication](apps/api/docs/auth.md)
- [Workspace setup](apps/api/docs/workspace-setup.md)
- [Daily workflows](apps/api/docs/daily-workflows.md)
- [Equity research](apps/api/docs/equity-research.md)
- [Go market worker](apps/go/market-worker/README.md)
- [Project state](docs/project-state.md)

## Contributing

Keep changes typed, validated, auditable, and covered by focused tests. Preserve deterministic artifacts as the source of truth, route candle data through shared normalization, and keep optional integrations fail-soft. Do not add broker execution or advisory claims under the existing product boundary.

## License

[MIT](LICENSE) © 2026 Waqas Raza
