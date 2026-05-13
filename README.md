# AI Trading Intelligence Agent

[![API CI](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml/badge.svg)](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml)
![Status](https://img.shields.io/badge/status-read--only%20market%20intelligence-blue)
![Safety](https://img.shields.io/badge/safety-no%20broker%20execution-success)
![API](https://img.shields.io/badge/API-FastAPI%20%2B%20Python%203.12-009688)
![Web](https://img.shields.io/badge/Web-Next.js%2015%20%2B%20React%2019-111111)
![Worker](https://img.shields.io/badge/Worker-Go%20market%20data%20sidecar-00ADD8)

## Candles Don't Lie

![Trading Candles](https://png.pngtree.com/png-clipart/20250227/original/pngtree-trading-candlestick-chart-pattern-with-sell-buy-indicator-in-red-green-png-image_20522223.png)

AI Trading Intelligence Agent is a read-only market intelligence product for daily review of
market data, deterministic signal context, data readiness, quality diagnostics, equity research,
and observed outcomes.

It is built around a Daily Trading Command Center and a deterministic FastAPI intelligence engine.
The product helps an operator review what is ready, what changed, what needs attention, and what
should be treated as stale, conflicted, or not actionable enough for review.

## Product Focus

The product turns structured market data and persisted intelligence artifacts into an auditable
daily review workflow.

It helps answer:

- Is the workspace ready for review today?
- Is the candle data fresh, complete, and good enough to trust?
- Which stored signals deserve review first?
- Which setups need confirmation, have conflicting evidence, or should be avoided for now?
- What changed in a watchlist, scanner run, daily brief, or equity research universe?
- What happened after earlier signals, and what should be reviewed in the journal?
- Which provider, data-quality, readiness, or diagnostic issues need cleanup?

## Current Product Surfaces

The web app in `apps/web` redirects `/` to `/command-center` and currently includes:

| Route                   | Product Role                                                                                                                                                      |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/command-center`       | Default daily cockpit for readiness, freshness, review-first setups, scanner context, workflow progress, notifications, and quality warnings.                     |
| `/onboarding`           | First-run status, workspace selector support, demo workspace option, and explicit safe setup actions.                                                             |
| `/setup`                | Guided workspace setup for workspace, symbols, sources, credential references, watchlists, scanner presets, preference profile, and optional demo candles.        |
| `/readiness`            | Product readiness checklist for API, DB, migrations, setup state, data freshness, worker state, and optional modules.                                             |
| `/brief`                | Daily/session/watchlist brief over persisted backend intelligence, with fail-soft frontend composition.                                                           |
| `/triage`               | Signal review board for Review First, Needs Confirmation, Conflicted, Avoid / No Directional, Stale / Data Issue, and Review Required.                            |
| `/signals/[signalId]`   | Read-only setup detail with visual chart context, evidence, confidence, outcomes, reasoning, historical cases, quality gates, audit, and journal panels.          |
| `/scanner`              | Watchlist scanner presets, scheduled scan configs, due scans, scan execution review, and scan result context.                                                     |
| `/equity-research`      | Equity swing research mode with universes, members, background data operations, metadata, fundamentals, earnings, catalysts, scans, and candidate review.         |
| `/data/onboarding`      | Data-source setup, candle freshness, provider health, gap planning, quality checks, and prepare-only recovery metadata.                                           |
| `/quality`              | Signal quality scoreboard over observed behavior, calibration, validation, drift, attribution, and data coverage.                                                 |
| `/review/outcomes`      | Outcome review queue with linked journal prompts and reliability diagnostics.                                                                                     |
| `/journal`              | Observation journal for reviewed, ignored, paper-followed, external-action-noted, or uncertain setup feedback.                                                    |
| `/notifications`        | In-app inbox for sanitized backend intelligence events, source links, delivery attempts, and review state.                                                        |
| `/dashboard`            | Broader operator dashboard for watchlists, signal focus, digests, backend state, and follow-up context.                                                           |
| `/symbols/[symbolId]`   | Symbol/timeframe state, market memory, recent signals, outcomes, scheduled scans, and analysis runs.                                                              |
| `/preferences/strategy` | Personal review preference profiles for filtering by market, symbol, session, timeframe, confidence, setup quality, stale-data tolerance, and confirmation rules. |
| `/demo`                 | Demo workspace flow for smoke validation with synthetic, clearly labeled data.                                                                                    |

The web client is intentionally fail-soft. Optional backend modules can be absent, and the UI should
show scoped empty states or backend-state warnings instead of breaking the daily workflow.

## Daily Review Loop

The intended operator loop is:

1. Open the Command Center and confirm workspace readiness.
2. Check provider health, candle freshness, stale data, and quality warnings.
3. Run an explicit daily workflow or scanner action when review inputs need refreshing.
4. Read the generated daily brief.
5. Triage stored signals by review priority, confirmation need, conflict, stale data, and safety state.
6. Inspect setup detail for evidence, setup context, final-candle chart context, outcomes, reasoning,
   historical cases, quality gates, and audit timeline.
7. Review equity research universes and candidates when the workspace includes equity swing research.
8. Add observational journal notes and review observed outcomes.
9. Clear in-app intelligence notifications and return to the Command Center summary.

Daily workflows record completed, skipped, and failed backend steps. They do not place orders,
execute broker actions, send external alerts by default, or call external providers unless polling
is explicitly enabled for that workflow and environment.

## Safety Boundary

Core rule:

```txt
Persisted artifacts are the source of truth. Deterministic engines classify and score. AI may only explain supplied evidence.
```

The system does:

- Ingest CSV/JSON candles, live feed candles, provider-polled candles, and equity research data.
- Normalize all candle paths through shared validation and storage contracts.
- Persist deterministic analysis artifacts, setup context, signal priority, market memory, daily
  briefs, signal digests, observed outcomes, journal notes, review items, notifications, and audit
  timelines.
- Use optional grounded AI/LLM layers only to explain, compare, or reason from supplied persisted
  evidence.
- Support explicit backend-safe actions such as readiness checks, scan runs, gap-recovery planning,
  journal follow-up, and outcome review.

The system does not:

- Place orders or connect to brokers for execution.
- Auto-trade, copy-trade, or create direct order instructions.
- Treat observed outcomes as account performance, P&L, or broker results.
- Let an LLM override deterministic signal classification or mutate source signals.
- Send external trading alerts from scans, digests, briefs, or reasoning output by default.
- Store raw provider secrets; credential references use opaque secret pointers.
- Provide regulated financial advice.

## Technical Architecture

This is a multi-app repository:

| Path                    | Role                                                                                                                                                               |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `apps/api`              | Canonical FastAPI backend, SQLAlchemy/Alembic schema, deterministic intelligence modules, auth/RBAC, read models, workers, and API docs.                           |
| `apps/web`              | Standalone Next.js App Router frontend with TypeScript, Tailwind CSS, typed API clients, read-only product surfaces, and mocked E2E smoke tests.                   |
| `apps/go/market-worker` | Additive Go sidecar for market data polling jobs, candle normalization, provider backpressure, circuit breaking, runtime heartbeats, and health/metrics endpoints. |
| `docs`                  | Repo-level architecture, development, deployment, roadmap, durable project state, and Codex working memory.                                                        |

Python remains the canonical API, product brain, orchestration layer, database contract owner, and
UI-facing contract layer. Go is additive and scoped to market data ingestion work where a sidecar is
a better operational fit.

## Backend Capabilities

Current backend capability groups include:

- Workspaces, users, auth/RBAC, permissions, product readiness, onboarding, workspace setup, demo
  mode, and workspace quick actions.
- Symbols, data sources, historical imports, live ingestion, provider polling, provider health,
  provider credential references, candle queries, candle quality, gap recovery, and ingestion
  performance tracking.
- Deterministic analysis lifecycle with features, indicators, patterns, strategy profiles, signal
  classification, evidence, confidence components, risk notes, setup context, explanations, and
  quality gates.
- Market sessions, regimes, multi-timeframe context, cross-asset context, market memory,
  historical-case search, decision readiness, and read-only intelligence reports.
- Signal priority, signal digests, daily briefs, daily workflows, daily routines, watchlists,
  scheduled scans, scanner presets, and bounded market scanning from stored final candles.
- Equity research universes, members, swing scans, candidate scoring, manual catalysts, equity data
  imports, metadata snapshots, fundamentals snapshots, earnings events, and queued background
  equity data operations with guarded stop, retry, summary, review queue, detail review, and
  lineage/diagnostics controls.
- Outcome evaluation, backtest cohorts, profile diagnostics, confidence calibration, walk-forward
  validation, cohort drift, pattern attribution, scenario outcome tracking, and review-focused
  analytics.
- Trading journal entries, operator reviews, notification inbox/outbox records, backend-safe action
  plans, artifact graph, audit timeline, intelligence catalog, capability registry, state-machine
  registry, reproducibility manifests, and dataset exports.
- Optional grounded LLM explanations, multi-LLM scenario reasoning, explanation comparison,
  context packs, AI insight cards, and chart screenshot extraction workflows with review gating.
- Runtime supervisor, distributed job queue, worker heartbeats, observability metrics, SLO
  snapshots, and internal operational health endpoints.

## Data And Execution Model

- Candles are normalized through shared validation before storage.
- Final candles are the default source for deterministic analysis.
- Imported, live, provider-polled, mock, and Go-worker-ingested candles converge on the same candle
  storage model.
- Read models are rebuildable and exist to make dashboard and command-center reads faster.
- Background work is explicit, bounded, auditable, and persisted through job/workflow/run records.
- Provider and notification integrations are gated by configuration and credential references.
- Demo and synthetic fixture paths are labeled and kept separate from production data assumptions.

## Run Locally

Start the Docker dev stack:

```sh
make dev
```

Apply migrations and seed deterministic defaults when needed:

```sh
make migrate
make seed
```

Open:

```txt
http://127.0.0.1:8000/health
http://127.0.0.1:3000/command-center
```

Run API or web directly without Docker:

```sh
./scripts/dev-api.sh
./scripts/dev-web.sh
```

Run the additive Go market data worker when Go is installed:

```sh
cd apps/go/market-worker
DATABASE_URL=postgresql://trading:trading@127.0.0.1:5432/trading_intelligence go run ./cmd/market-worker
```

The API uses Python packaging from `apps/api/pyproject.toml`. The web app uses npm with the
committed `apps/web/package-lock.json`; use `npm ci` for clean installs. Only public frontend
configuration belongs in `NEXT_PUBLIC_*` variables.

## Quality Checks

API checks:

```sh
make api-check
```

Web checks:

```sh
make web-check
```

Repository whitespace check:

```sh
git diff --check
```

Focused commands used frequently in this repo:

```sh
cd apps/api && ruff check app alembic
cd apps/api && pytest
cd apps/web && npm run typecheck
cd apps/web && npm run lint
cd apps/web && npm run test:e2e
cd apps/go/market-worker && go test ./...
```

Some checks require installed local dependencies, a configured database, or Go tooling.

## Documentation

- [API README](apps/api/README.md)
- [Web app README](apps/web/README.md)
- [Go market worker README](apps/go/market-worker/README.md)
- [Development setup](docs/development.md)
- [Deployment](docs/deployment.md)
- [Onboarding](apps/api/docs/onboarding.md)
- [Workspace setup](apps/api/docs/workspace-setup.md)
- [Product readiness](apps/api/docs/product-readiness.md)
- [Daily briefs](apps/api/docs/daily-briefs.md)
- [Daily workflows](apps/api/docs/daily-workflows.md)
- [Daily routines](apps/api/docs/daily-routines.md)
- [Scanner presets](apps/api/docs/scanner-presets.md)
- [Equity research](apps/api/docs/equity-research.md)
- [Equity data](apps/api/docs/equity-data.md)
- [Go market worker](apps/api/docs/go-market-worker.md)
- [Job queue](apps/api/docs/job-queue.md)
- [Provider health](apps/api/docs/provider-health.md)
- [Provider credentials](apps/api/docs/provider-credentials.md)
- [Signal priority](apps/api/docs/signal-priority.md)
- [Setup context](apps/api/docs/setup-context.md)
- [Trading journal](apps/api/docs/trading-journal.md)
- [Notifications](apps/api/docs/notifications.md)
- [Observability](apps/api/docs/observability.md)
- [Project state](docs/project-state.md)

## Contributing

- Keep product copy informational, non-advisory, and clear about review-only behavior.
- Preserve deterministic artifacts as the source of truth.
- Keep frontend workflows tolerant of missing optional backend endpoints.
- Route candle data through shared normalization and validation.
- Keep backend modules small, typed, validated, and auditable.
- Do not store raw secrets in code, docs, memory files, queued payloads, or API responses.
- Add focused tests for new product behavior and run the relevant checks before pushing.
- Keep commit messages under 140 characters.

## License

This repository is published under a restrictive proprietary license. All rights are reserved, and
use, copying, modification, distribution, hosting, sublicensing, or commercialization requires prior
written permission from the copyright holder. See [LICENSE](LICENSE).
