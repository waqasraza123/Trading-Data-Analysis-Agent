# AI Trading Intelligence Agent

[![API CI](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml/badge.svg)](https://github.com/waqasraza123/Trading-Data-Analysis-Agent/actions/workflows/api-ci.yml)
![Status](https://img.shields.io/badge/status-daily%20dashboard%20%2B%20intelligence%20backend-blue)

AI Trading Intelligence Agent is a deterministic market-intelligence product for daily review of
market data, signal context, data readiness, quality diagnostics, and observed outcomes.

The product is centered on a read-only Daily Trading Command Center backed by a FastAPI intelligence
engine. It helps an operator answer practical review questions:

- Is the market data fresh enough to review?
- What changed since the last scan or brief?
- Which stored signals deserve attention first?
- Which setups need confirmation, have conflicting evidence, or should be avoided for now?
- What happened after earlier signals, and what should be reviewed in the journal?
- Which provider, data-quality, or diagnostic issues need cleanup before analysis is trusted?

It is not a trading bot, broker terminal, copy-trading platform, external alerting product, or
financial-advice system.

## Product Boundary

The product turns structured market data and persisted intelligence artifacts into an auditable
daily review workflow.

It does:

- Ingest historical CSV/JSON candles and live/provider-originated candle data.
- Normalize imported, live, and provider-polled candles through one shared validation path.
- Store final and partial candle state with freshness, gap, and quality metadata.
- Run deterministic analysis, pattern, indicator, setup-context, signal-priority, and quality
  workflows.
- Persist daily briefs, signal digests, market memory, setup context, observed outcomes, journal
  notes, notification inbox events, and audit timelines.
- Provide a web command center for daily review, triage, scanner management, quality diagnostics,
  outcome review, preferences, journal notes, and data onboarding.
- Use optional grounded AI/LLM layers only to explain or reason from supplied persisted evidence.

It does not:

- Place orders or connect to brokers for execution.
- Auto-trade, copy-trade, or create direct order instructions.
- Let an LLM override deterministic classification or mutate source signals.
- Treat observed outcomes as account performance, P&L, or broker results.
- Send external alerts by default from scan, digest, or brief generation.
- Provide regulated financial advice.

Core rule:

```txt
Persisted artifacts are the source of truth. Deterministic engines classify and score. AI may only explain supplied evidence.
```

## Daily Workflow

The implemented daily product loop is:

1. Check data freshness in the Command Center or Data Onboarding.
2. Run the daily workflow to refresh provider health, prepare recovery plans, run deterministic
   scans, generate setup context, score review priority, refresh market memory, create signal
   digests, and generate a persisted brief.
3. Apply scanner presets when a repeatable session, watchlist, volatility, pattern, or data-repair
   configuration is useful.
4. Read the daily brief for workspace-level review context.
5. Triage stored signals by quality, confirmation need, conflict, stale data, and review status.
6. Inspect setup detail for evidence, confidence, zones, invalidation context, outcomes, reasoning,
   historical cases, quality findings, audit timeline, and journal context.
7. Add observational journal notes.
8. Review observed outcomes and quality diagnostics.
9. Review in-app intelligence notifications and return to the Command Center summary.

The daily workflow records completed, skipped, and failed backend steps. It does not execute broker
actions, execute external notifications, or call external providers unless provider polling is
explicitly enabled for that workflow.

## Implemented Web Surfaces

The web app in `apps/web` redirects `/` to `/command-center` and includes these product routes:

| Route | Purpose |
| --- | --- |
| `/command-center` | Default daily start page for freshness, changes, review-first setups, scanner status, notifications, quality warnings, and next actions. |
| `/brief` | Workspace daily brief, preferring the persisted backend brief and falling back to frontend composition when optional endpoints are missing. |
| `/triage` | Read-only signal triage board across high-quality context, needs confirmation, conflicted, avoid/no directional signal, stale/data issue, and review required. |
| `/scanner` | Watchlist scanner controls, scanner presets, scheduled scan configs, due scans, and scan result review. |
| `/signals/[signalId]` | Full setup detail for one stored signal, including evidence, confidence, setup context, outcomes, quality, reasoning, audit, and journal panels. |
| `/dashboard` | Daily operator cockpit over watchlists, signal focus, digests, avoid conditions, backend state, and follow-up context. |
| `/symbols/[symbolId]` | Symbol/timeframe state, market memory, recent signals, outcomes, scheduled scans, and analysis runs. |
| `/data/onboarding` | Data-source setup, freshness checks, candle quality, provider health, gap planning, and prepare-only recovery metadata. |
| `/quality` | Signal quality scoreboard over observed behavior, calibration, validation, drift, attribution, and data coverage. |
| `/review/outcomes` | Outcome review queue with linked journal prompts and optional reliability diagnostics. |
| `/journal` | Observation journal for reviewed, ignored, paper-followed, external-action-noted, or uncertain setup feedback. |
| `/preferences/strategy` | Personal review preference profiles for filtering by market, symbol, session, timeframe, confidence, setup quality, stale-data tolerance, and confirmation requirements. |
| `/notifications` | In-app inbox for sanitized backend intelligence events, safety state, delivery attempts, and source links. |

The web client tolerates missing optional backend modules with scoped empty states and backend-state
warnings instead of crashing the workflow.

## Intelligence Capabilities

Current backend capabilities include:

- Workspace, user, symbol, and data-source management.
- Historical import, live ingestion, provider polling, candle queries, candle quality, and gap
  recovery planning.
- Analysis lifecycle with deterministic feature, indicator, pattern, strategy-profile, signal,
  evidence, confidence, risk-note, and explanation artifacts.
- Setup context, market regimes, market sessions, multi-timeframe context, cross-asset context,
  market memory, historical-case search, and decision readiness.
- Signal priority scoring, signal digests, daily briefs, and daily workflow orchestration.
- Watchlists, scheduled scans, scanner presets, scan runs, and bounded market scanning from stored
  final candles.
- Observed outcome evaluation, backtest cohorts, profile diagnostics, confidence calibration,
  walk-forward validation, cohort drift, pattern attribution, and quality gates.
- Trading journal entries, operator review queue, notification event inbox, backend-safe action
  plans, audit timelines, artifact graph, capability registry, state-machine registry, and
  reproducibility manifests.
- Optional grounded deterministic/AI explanation, scenario reasoning, scenario ensemble, scenario
  outcome, explanation comparison, context pack, intelligence report, and dataset export surfaces.
- Chart screenshot candle extraction and deterministic trend-hypothesis workflows with review
  gating for low-confidence extraction.
- Worker runtimes for live feeds, stale checks, market scans, reasoning actions, notifications, and
  supervisor orchestration.

## Run Locally

Start the full Docker dev stack:

```sh
make dev
```

Then apply migrations and seed deterministic defaults when needed:

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

## Documentation

- [Web app README](apps/web/README.md)
- [API README](apps/api/README.md)
- [Development setup](docs/development.md)
- [Deployment](docs/deployment.md)
- [Daily briefs](apps/api/docs/daily-briefs.md)
- [Daily workflows](apps/api/docs/daily-workflows.md)
- [Scanner presets](apps/api/docs/scanner-presets.md)
- [Signal priority](apps/api/docs/signal-priority.md)
- [Setup context](apps/api/docs/setup-context.md)
- [Provider health](apps/api/docs/provider-health.md)
- [Notifications](apps/api/docs/notifications.md)
- [Trading journal](apps/api/docs/trading-journal.md)
- [Intelligence quality](apps/api/docs/intelligence-quality.md)
- [Project state](docs/project-state.md)

## Contributing

- Keep product copy informational, non-advisory, and clear about review-only behavior.
- Preserve deterministic artifacts as the source of truth.
- Keep frontend workflows tolerant of missing optional backend endpoints.
- Keep backend modules small, typed, validated, and auditable.
- Route candle data through shared normalization and validation.
- Add focused tests for new product behavior and run the relevant checks before pushing.
- Keep commit messages under 140 characters.

## License

No license file is currently published for this repository. Add a license before distributing,
packaging, or accepting external contributions.
