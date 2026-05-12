# Trading Intelligence API

Demo mode is implemented under `/demo-mode`. It can create a labeled demo workspace, seed demo
symbols and a synthetic JSON import source, import deterministic fixture candles, run deterministic
analysis, create signals, build setup context, score review priority, evaluate observed outcomes,
create scanner artifacts, persist a daily brief, and optionally create a journal note. It is for
local/staging product validation only: no external providers, broker execution, auto-trading, or
financial advice. Enable it with `DEMO_MODE_ENABLED=true` outside development. See
`docs/demo-mode.md`.

Production auth and workspace RBAC are implemented under `/auth`, `/permissions`,
`app.modules.auth`, and `app.modules.permissions`. The layer supports dev headers,
first-party password sessions, legacy admin API keys, hashed persisted API keys, RS256 JWT verification, current
identity/context routes, workspace isolation, and reusable permission dependencies.
`AUTH_ENABLED=false` plus `AUTH_MODE=dev` remains the local/test default. See
`docs/auth.md`, `docs/permissions.md`, and `docs/rbac-route-coverage.md`.

Workspace overview and quick actions are implemented under
`/workspaces/{workspace_id}/overview` and `/workspaces/{workspace_id}/quick-actions`.
The overview endpoint composes persisted readiness, provider health, data freshness,
daily brief, workflow, read model, outcome, notification, journal, and quality artifacts
into one command-center payload while reporting missing sections safely. Quick actions
run explicit backend-safe daily tasks only and do not perform broker execution,
auto-trading, copy trading, external notification delivery, or financial-advice behavior.
See `docs/workspace-overview.md` and `docs/workspace-quick-actions.md`.

First-run onboarding is implemented under `/onboarding`. It composes workspace, operator, symbols,
data sources, provider/data freshness, watchlist, scan config, daily workflow, product readiness,
and demo-mode state into one setup status response. Explicit onboarding actions can create safe
setup records or run a readiness/demo flow without hidden provider polling, broker execution,
auto-trading, external notifications, or financial advice. `/workspaces/default-context` returns a
read-only default workspace/user context without creating records. See `docs/onboarding.md`.

The web app has a Playwright daily workflow smoke harness that uses mocked API responses for
onboarding, workspace context, command-center overview, and backend-safe quick actions. It
complements the backend smoke and unit tests without requiring `DATABASE_URL`, a running API
process, external providers, LLM credentials, or notification delivery.

Scanner presets are implemented under `/scanner-presets`. They seed opinionated templates for
London open, New York open, crypto 24h, volatility, pattern context, data repair, and close-of-day
review workflows. Applying a preset creates watchlists and scheduled scan configs only; it does not
run scans, create execution setups, send alerts, call brokers, auto-trade, or provide financial
advice. See `docs/scanner-presets.md`.

Equity research mode is implemented under `/equity-research`. It adds workspace-scoped stock
universes, manual universe members, deterministic swing scan runs, ranked swing setup candidates,
component scoring, and manual catalyst context. It reads existing symbols, candles, analysis
artifacts, setup context, signal priority context, data quality, provider health, and news/event
artifacts where available. It does not fetch external fundamentals automatically, place orders,
connect to brokers for execution, auto-trade, mutate final signal classifications, call LLMs for
classification, or provide financial advice. See `docs/equity-research.md`.

Equity data provider foundations are implemented under `/equity-data`. They support deterministic
mock universe import, CSV/JSON row import, symbol metadata snapshots, fundamentals snapshots,
earnings events, provider request audit rows, import errors, credential-reference-aware provider
skeletons, earnings-to-catalyst conversion, CSV file uploads, and queued background operations for
larger import/enrichment work. External provider calls are disabled by default, raw uploaded files
are not persisted, and raw provider secrets are not stored. See `docs/equity-data.md`.

Product readiness is implemented under `/product-readiness`. It persists an operator-facing
checklist run for API reachability, database/migration detectability, seed/workspace/user setup,
symbols, data sources, provider credentials, provider health, candle freshness, watchlists, scan
configs, daily workflow availability, worker status, optional notifications, journal readiness, web
API reachability, and critical stale/missing data indicators. It validates readiness only; it does
not seed data, run scans, run daily workflows, start workers, call providers, send notifications,
execute broker actions, auto-trade, or provide financial advice. See `docs/product-readiness.md`.

Guided workspace setup is implemented under `/workspace-setup`. It persists auditable setup runs
and step results for workspace, operator, symbols, source, credential reference, watchlist, scanner
preset, preference profile, optional synthetic demo candles, readiness validation, and an optional
explicit first deterministic scan. It does not store raw secrets, connect to brokers for orders,
execute broker actions, auto-trade, send external signal delivery, run hidden scans, or provide financial advice. See
`docs/workspace-setup.md`.

Runtime supervisor APIs are implemented under `/runtime-supervisor`. They seed worker definitions,
record optional worker heartbeats, mark stale workers, summarize runtime health, and record safe
operator run requests for existing backend workers. They do not start OS processes, execute shell
commands, call brokers, auto-trade, mutate signals outside existing backend-safe workflows, or
provide financial advice. See `docs/runtime-supervisor.md`.

Distributed job queue APIs are implemented under `/job-queue`. The default backend is DB-backed and
supports enqueue, claim, heartbeat, retry/backoff, cancellation, priority, scheduling,
idempotency keys, dead-letter state, worker queues, payload validation, and metrics-ready status
fields for backend workloads. The Redis adapter path exists without requiring Redis locally. It does
not execute broker/order jobs, arbitrary code, shell commands, auto-trading, or financial-advice
behavior. See `docs/job-queue.md`.

Daily routine templates are implemented under `/daily-routines`. They seed named operator
routines such as pre-market scan, London/New York open review, crypto 24h review, close-of-day
review, stale-data repair, outcome review, quality review, and journal follow-up. Routine runs
compose explicit bounded backend-safe steps only; they do not place orders, call brokers,
auto-trade, suggest directional actions, deliver external notifications by default, or provide
financial advice. See `docs/daily-routines.md`.

Personal strategy preference profiles are implemented under `/preference-profiles`. They let a
workspace or user define preferred markets, symbols, sessions, timeframes, patterns, confidence
thresholds, setup-quality thresholds, stale-data tolerance, confirmation requirements, avoid lists,
and notification preference categories for review workflows only. They do not mutate deterministic
strategy profiles, change signal classification, execute broker workflows, auto-trade, copy-trade,
or provide financial advice. See `docs/preference-profiles.md`.

Actionable setup context is implemented under `/signals/{id}/setup-context` and
`/analysis-runs/{id}/setup-context`. It persists structured non-advisory setup context from existing
signals, evidence, confidence, risk notes, advanced features, market regime/session context,
multi-timeframe context, cross-asset context, outcomes, data quality, and readiness artifacts. It
uses invalidation context, observation zones, target context zones, wait conditions, avoid reasons,
data-quality warnings, risk notes, and backend-safe next observations. It does not mutate signals or
strategy profiles, execute action items, send alerts, place orders, call brokers, auto-trade, call
LLMs for classification, or provide financial advice.

Deterministic signal review priority scoring is implemented under
`/signals/{id}/priority-score` and `/signal-priorities`. It persists review priority scores,
labels, buckets, component scores, penalties, boosters, reasons, and warnings from existing stored
artifacts. It helps triage which signals deserve human review first. It is not a trading score, not
directional advice, does not mutate signals or classifiers, does not execute broker workflows, and
does not provide financial advice. See `docs/signal-priority.md`.

Trading journal feedback is implemented under `/journal-entries`. It records user/operator
decision notes around observed, ignored, reviewed, paper-followed, or externally handled setups and
compares those notes with later deterministic outcomes. It does not add UI, broker execution,
broker imports, auto-trading, copy trading, financial advice, account-return calculations, signal mutation, or
outcome mutation.

Signal digests are implemented under `/signal-digests`. They persist deterministic daily, session,
custom-period, and watchlist review summaries from stored signals, outcomes, market memory, quality
gates, readiness checks, news/event correlations, and backend follow-up records. They do not run
analysis, evaluate outcomes, call LLMs, classify or override signals, send notifications, execute
broker actions, auto-trade, copy-trade, or provide financial advice.

Daily briefs are implemented under `/daily-briefs` and
`/workspaces/{workspace_id}/daily-brief/latest`. They persist the canonical backend daily command
center contract from existing stored artifacts, including signal digests, market memory, signal
priority, setup context, provider health, data quality, outcomes, backend-safe action items,
watchlists/scans, decision readiness, market regimes/sessions, multi-timeframe context,
cross-asset context, and journal follow-ups. They do not trigger scans, provider polling, outcome
evaluation, LLM calls, notifications, action execution, broker workflows, auto-trading, or
financial advice. See `docs/daily-briefs.md`.

Dashboard read models are implemented under `/read-models`. They materialize rebuildable snapshots
for dashboard symbol state, signal triage cards, and command center summaries from existing stored
artifacts. They improve daily cockpit reads without changing source-of-truth signals, market
memory, setup context, priority scores, outcomes, provider health, data quality, readiness,
briefs, or reports. Rebuild endpoints create or update snapshot rows only; they do not run
analysis, scans, outcome evaluation, LLM calls, notifications, broker workflows, auto-trading, or
financial-advice flows. See `docs/read-models.md`.

Pattern detector attribution is implemented under `/pattern-attribution`. It evaluates how stored
pattern candidates contributed to final signals and observed outcomes by detector type, selected
candidate, rejected candidate, blocked candidate, horizon, profile, symbol, and timeframe. It is
diagnostic only: it does not mutate candidates or detectors, change final signal classification,
auto-tune profiles, call LLMs, send alerts, execute broker actions, or provide financial advice.

Rolling market state memory is implemented under `/market-memory`. It stores one latest
deterministic context snapshot per workspace, symbol, optional source, timeframe, and state version
for faster reporting, scans, readiness checks, and future UI. It reads persisted final candles and
deterministic artifacts only; it does not run analysis, evaluate outcomes, call LLMs, mutate
signals, send alerts, execute broker actions, auto-trade, or provide financial advice.

Signal cohort drift detection is implemented under `/cohort-drift`. It compares recent stored
signal/outcome behavior against a baseline period by cohort and horizon, stores drift labels,
severity, safe rate deltas, confidence alignment drift, low-sample states, and review metadata. It
does not mutate signals or outcomes, modify strategy profiles, call LLMs, send alerts, execute
broker actions, or provide financial advice.

Scenario hypothesis outcome tracking is implemented under `/reasoning/scenarios`,
`/reasoning/runs`, and `/scenario-outcomes`. It compares persisted scenario hypotheses with stored
signal outcomes, writes separate support-label rows and summary runs, and does not call LLMs,
generate new scenarios, mutate source artifacts, execute broker actions, or provide financial
advice.

Walk-forward validation is implemented under `/walk-forward-validations`. It analyzes stored
deterministic signals and stored outcomes across chronological validation windows to summarize
observed follow-through, reversal behavior, confidence alignment, stability, degradation, and
sample-size coverage. It does not evaluate missing outcomes, mutate signals, modify strategy
profiles, perform broker accounting, send alerts, execute broker actions, or provide financial advice.

The intelligence capability registry is implemented under `/capabilities`. It documents installed
backend intelligence modules, API references, input and output contracts, produced artifacts,
dependencies, runtime availability, provider credential requirements, execution type, and safety
level. It is metadata/configuration only and does not run modules, call providers, mutate
intelligence artifacts, send alerts, execute broker actions, auto-trade, or provide financial
advice.

Deterministic synthetic candle fixtures are implemented under `app.modules.synthetic_fixtures`
with an optional guarded `/synthetic-fixtures/generate` endpoint and
`python -m app.cli synthetic-fixtures generate` CLI helper. They create repeatable development and
testing OHLC inputs only; they do not fetch external data, mutate production data, run analysis,
send alerts, execute broker actions, auto-trade, or provide financial advice.

These deterministic modules connect through persisted artifacts only: market memory summarizes the
latest context, cohort drift and pattern attribution read stored signal outcomes, scenario outcomes
read persisted scenario hypotheses and outcomes, and synthetic fixtures only generate exportable
inputs for development and tests.

Cross-asset context support is implemented under `/analysis-runs/{id}/cross-asset-context`,
`/signals/{id}/cross-asset-context`, and `/cross-asset-context/runs/{id}/results`. It compares
stored final candles across related symbols for deterministic correlation, co-movement, divergence,
and possible lead/lag context only. It does not infer causation, mutate signals, provide financial
advice, send alerts, call LLMs, or execute broker actions.

Confidence calibration analytics are implemented under `/confidence-calibration`. They compare
persisted deterministic confidence scores with observed follow-through outcomes by confidence bin,
horizon, and optional profile/pattern/symbol/timeframe filters. This is reliability analysis only:
it does not calculate broker accounting metrics, provide financial advice, mutate signals, change classifiers,
auto-adjust profiles, send alerts, or execute broker actions.

Market session context support is implemented as a deterministic backend-only layer for analysis
runs and signals. It stores rough UTC session context for grouping and audit only; it does not use
external exchange calendars, mutate signal classification, send alerts, execute trades, or provide
financial advice.

Operator review queue support is implemented as a backend-only workflow layer for human review of
intelligence artifacts. It records review state and audit events only; it does not provide UI,
notifications, alerts, broker execution, trade approval, source signal mutation, strategy profile
mutation, LLM calls, or financial advice.

FastAPI backend for deterministic market intelligence over imported and live-originated
candle data. The backend stores market data, calculates features and indicators, classifies
signals with rules, generates safe deterministic and optional grounded LLM explanations from
persisted artifacts, supports optional multi-LLM grounded scenario reasoning and scenario ensemble
consensus diagnostics, compares persisted explanation layers for deterministic disagreement
analysis, supports replay from
stored candles, persists deterministic news/event context, evaluates observed historical outcomes
after persisted signals, stores outcome-based profile diagnostics and advisory calibration
recommendations, converts persisted reasoning scenarios into backend-safe follow-up action plans,
composes read-only intelligence reports from existing persisted artifacts, persists deterministic
intelligence quality gate runs with diagnostic shadow classification comparisons, and can run
backend-only market watchlist scans that create bounded deterministic analysis runs from stored
final candles. It also accepts manually or externally extracted trading chart screenshot candles and
persists deterministic next-trend hypotheses. A read-only audit timeline API composes persisted
artifacts into chronological traceability and lineage views for operator review.

Market data provider polling is implemented as backend-only candle ingestion through provider
adapters under `/provider-polling`. It supports a deterministic mock provider, Binance public REST
klines without credentials, and a safe generic OHLC HTTP stub. Provider polling requires
`api_polling` data sources and normalizes into the existing candle validator/repository path.

Candle ingestion performance diagnostics are implemented under `/candle-ingestion`. CSV imports,
JSON imports, and provider polling now create performance run records with batch counts, elapsed
time, insert/update/duplicate/conflict/failure counts, and conflict drilldowns. The path keeps
existing validation and final/partial candle semantics, and the COPY-style path remains disabled by
default. See `docs/candle-ingestion-performance.md`.

Candle gap recovery planning is implemented under `/candle-gap-recovery`. It detects missing final
candles in live or imported datasets, groups adjacent missing timestamps into recovery items,
records provider-polling/manual-import planning metadata, and can create pending provider polling
request rows without executing external provider fetches.

Provider health snapshots are implemented under `/provider-health`. They aggregate persisted data
source state, candle freshness, missing candles, provider polling successes/failures, live
subscription state, data quality, market memory, and gap recovery plans into an operational data
reliability workflow. They do not call external providers, mutate candles, auto-create polling
requests outside the explicit gap recovery route, execute broker actions, send alerts, auto-trade,
or provide financial advice.

Provider credential references are implemented under `/provider-credentials`. They store
workspace-scoped `secret_ref` pointers and redacted public metadata for data providers and delivery
channels only. Raw API keys, tokens, passwords, webhook secrets, and broker credentials are not
stored in plaintext or returned by the API. Connection tests record safe configuration, mock,
public-endpoint, or skipped authenticated checks without requiring real credentials at startup.
Nullable `credential_ref_id` fields are available on data sources, live subscriptions, provider
polling requests, notification channels, and webhook subscriptions. See
`docs/provider-credentials.md`.

Daily workflows are implemented under `/daily-workflows`. They persist one auditable backend
orchestration for refreshing provider health, preparing recovery plans, running deterministic
scheduled scans, generating setup context, scoring review priority, refreshing market memory,
generating signal digests, and generating daily brief records when that backend module is installed.
They do not execute broker actions, execute notifications, auto-trade, call external providers
unless provider polling is explicitly enabled, or provide financial advice. See
`docs/daily-workflows.md`.

The integrated daily product flow is data freshness -> run workflow -> scanner presets -> brief ->
triage -> setup detail -> journal/outcome review. Notifications are in-app intelligence events for
review state only, not external delivery by default. Quality scoreboard data is observed behavior
and diagnostics only, not account-performance or broker-result reporting.

The daily workflow merge reconciles the daily brief, workflow run, scanner preset, quality
scoreboard, and notification inbox surfaces into one review loop. Existing deterministic artifacts
remain the source of truth; workflow records only orchestrate bounded backend-safe services and
persist the artifacts they create.

Daily workflow integration uses these backend modules together without adding broker execution:

```txt
/provider-health
/signal-priorities
/preference-profiles
/journal-entries
/signals/{signal_id}/outcomes
```

The intended product loop is data freshness, deterministic scan, review-priority ranking, triage,
setup inspection, journal reflection, and observed outcome review. Stored deterministic artifacts
remain the source of truth.

No UI, broker execution, auto-trading, alerts, or billing is implemented in this backend slice.
LLM layers are optional and may only explain or reason from persisted deterministic output.
Market regime context is deterministic metadata only and does not alter signal classification.

The first read-only frontend surface now lives in `apps/web`. It consumes this API through
`NEXT_PUBLIC_API_BASE_URL`, renders missing optional endpoints as safe empty states, and keeps
broker execution and auto-trading outside the product boundary.

The web data onboarding route at `/data/onboarding` uses existing backend contracts for
`/data-sources`, `/symbols`, `/candles/latest`, `/candles/count`, `/candles/quality`,
`/data-quality/candle-range/run`, `/market-memory/snapshots`, `/live/subscriptions`,
`/provider-polling/requests`, and `/candle-gap-recovery`. It prepares recovery metadata with
`createRequests=false` and does not execute external provider fetches. Provider credentials remain
server-side; the UI does not accept provider API keys.

The same route also reads `/provider-health` when available to show provider/source health, stale or
missing candles, recent polling failures, prepare-only recovery planning, and deterministic-analysis
readiness.

The integrated daily workflow pages in `apps/web` prefer the backend daily brief when available.
`/brief` and `/command-center` read `/workspaces/{workspace_id}/daily-brief/latest` first, then
fall back to the existing frontend composition over provider health, market memory, signal
priority, preference profiles, signals, outcomes, setup context, decision readiness, action items,
operator reviews, signal digests, watchlists, scheduled scans, data-quality, market
sessions/regimes, intelligence reports, audit timelines, and journal APIs. Missing optional
endpoints should return 404 or standard API errors; the web client maps those into safe fallback
states.

The integrated dashboard surface now reads signal digests and setup context when those endpoints
are available. Digest items may reference setup context rows, and journal entries can link to setup
context rows for later deterministic review. Notification events remain optional, explicitly
created, safety-filtered, and never auto-delivered by digest or setup-context generation.

Capability registry endpoints:

```txt
GET /capabilities
GET /capabilities/{key}
POST /capabilities/seed-default
GET /capabilities/summary
```

Synthetic fixture generation endpoint:

```txt
POST /synthetic-fixtures/generate
```

The endpoint is disabled unless `SYNTHETIC_FIXTURES_API_ENABLED=true` and is unavailable in
production. The CLI helper does not require database access.

## Commands

Install dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

From the repository root, the same setup is wrapped by:

```sh
./scripts/dev-api.sh
make api-check
make migrate
make seed
```

The API uses `pyproject.toml` as the dependency source of truth. The production Docker image also
uses `constraints-runtime.txt` to pin runtime dependency resolution. Local development and CI keep
using the `dev` extra so pytest, Ruff, mypy, and HTTP test tooling stay outside the runtime image.

Build the production Docker image from the repository root:

```sh
docker build -f apps/api/Dockerfile -t trading-intelligence-api:latest .
```

Run the production image with runtime configuration injected by the orchestrator:

```sh
docker run --rm -p 8000:8000 \
  -e APP_ENV=production \
  -e DATABASE_URL=postgresql://user:password@host:5432/trading \
  -e AUTH_ENABLED=true \
  -e AUTH_MODE=api_key \
  -e ADMIN_API_KEY=replace-with-secret-from-secret-manager \
  trading-intelligence-api:latest
```

`DATABASE_URL` is optional for liveness startup but required for database-backed product routes,
migrations, and workers. Production auth should use `AUTH_MODE=api_key`, `AUTH_MODE=jwt`, or
`AUTH_MODE=mixed`; when legacy API-key enforcement is enabled, set `ADMIN_API_KEY` and
`API_KEY_HEADER_NAME`.

Run the local compose stack:

```sh
docker compose up --build api postgres redis
```

Run the development Docker image with reload:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build api
```

The production image installs runtime dependencies only, runs as a non-root user, exposes `8000`,
and uses `/health/live` as a liveness healthcheck. Secrets must be injected at runtime.

Run the development server:

```sh
.venv/bin/uvicorn app.main:app --reload
```

Run migrations:

```sh
.venv/bin/alembic upgrade head
```

Run product readiness:

```sh
curl -X POST "http://127.0.0.1:8000/product-readiness/run?workspaceId=<workspace-id>"
curl "http://127.0.0.1:8000/product-readiness/latest?workspaceId=<workspace-id>"
```

Start guided workspace setup:

```sh
curl -X POST "http://127.0.0.1:8000/workspace-setup/start" \
  -H "content-type: application/json" \
  -d '{"metadata":{"source":"local"}}'
curl "http://127.0.0.1:8000/workspace-setup/runs/<setup-run-id>"
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
current engine versions, and default scanner presets.
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

Generate deterministic synthetic candle fixture CSV:

```sh
.venv/bin/python -m app.cli synthetic-fixtures generate --pattern bullish_breakout --output-format csv
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
GET /runtime-supervisor/health
GET /observability/slo
GET /observability/metrics
GET /observability/metrics.json
GET /observability/tracing/status
```

`/health` and `/health/live` only prove the API process is alive. `/health/db` checks
database connectivity. `/health/ready` requires database connectivity and valid critical
configuration. `/health/workers` reports live worker and stale monitor state when a database is
configured, and returns a safe degraded status otherwise.
`/runtime-supervisor/health` reports seeded runtime worker definitions, worker heartbeats, stale
instances, and runtime run request counters after migrations are applied.
`/observability/*` exposes internal production observability metrics, SLO status, and tracing
status. It requires no external observability provider at startup.

Run the live feed worker:

```sh
.venv/bin/python -m app.workers.live_feed_worker
```

Run the stale monitor:

```sh
.venv/bin/python -m app.workers.live_stale_monitor
```

Run the reasoning action worker:

```sh
REASONING_ACTION_WORKER_ENABLED=true .venv/bin/python -m app.workers.reasoning_actions_worker
```

Run the notification worker:

```sh
NOTIFICATION_WORKER_ENABLED=true .venv/bin/python -m app.workers.notification_worker
```

Run the market scan worker:

```sh
MARKET_SCAN_WORKER_ENABLED=true .venv/bin/python -m app.workers.market_scan_worker
```

Run a job queue worker:

```sh
.venv/bin/python -m app.workers.job_queue_worker --queue scans
```

Run a supervised worker process:

```sh
WORKER_SUPERVISOR_COMPONENTS=live_feed,stale_monitor,reasoning_actions,notifications,market_scans \
REASONING_ACTION_WORKER_ENABLED=true \
NOTIFICATION_WORKER_ENABLED=true \
MARKET_SCAN_WORKER_ENABLED=true \
.venv/bin/python -m app.workers.supervisor
```

Security and traffic controls are configured through environment variables:

```txt
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=false
AUTH_ENABLED=false
AUTH_MODE=dev
AUTH_JWT_ENABLED=false
AUTH_API_KEYS_ENABLED=true
AUTH_PASSWORD_ENABLED=true
AUTH_PASSWORD_SIGNUP_ENABLED=true
AUTH_SESSION_TTL_MINUTES=1440
AUTH_PASSWORD_FAILED_ATTEMPT_LIMIT=8
AUTH_PASSWORD_LOCKOUT_MINUTES=15
AUTH_DEV_USER_EMAIL=
AUTH_DEV_WORKSPACE_ID=
JWT_ISSUER=
JWT_AUDIENCE=
JWT_PUBLIC_KEY=
JWT_ALGORITHM=RS256
ADMIN_API_KEY=
API_KEY_HEADER_NAME=x-api-key
USER_CONTEXT_HEADER_NAME=x-user-id
WORKSPACE_CONTEXT_HEADER_NAME=x-workspace-id
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_ENABLED=false
RATE_LIMIT_REQUESTS_PER_MINUTE=60
MAX_REQUEST_BODY_BYTES=1048576
MAX_UPLOAD_FILE_BYTES=10485760
CHART_OCR_ENABLED=false
CHART_OCR_PROVIDER=google_vision
CHART_OCR_TIMEOUT_SECONDS=10
CHART_OCR_MIN_CONFIDENCE=0.6500
CHART_IMAGE_MIN_EXTRACTION_CONFIDENCE=0.7500
DATA_QUALITY_VERSION=v1
DATA_QUALITY_STRONG_THRESHOLD=0.9500
DATA_QUALITY_ACCEPTABLE_THRESHOLD=0.8500
DATA_QUALITY_DEGRADED_THRESHOLD=0.7000
DATA_QUALITY_OUTLIER_RANGE_MULTIPLIER=5.0000
DATA_QUALITY_STALE_LIVE_SECONDS=300
CHART_UNSUPPORTED_REJECTION_ENABLED=true
AUDIT_TIMELINE_MAX_EVENTS=200
AUDIT_TIMELINE_MAX_AUDIT_EVENTS=100
AUDIT_TIMELINE_MAX_ARTIFACTS=200
AUDIT_TIMELINE_REDACTION_ENABLED=true
INTELLIGENCE_QUALITY_GATE_VERSION=quality_gates_v1
INTELLIGENCE_QUALITY_SHADOW_VERSION=shadow_profiles_v1
INTELLIGENCE_QUALITY_STRONG_THRESHOLD=0.9000
INTELLIGENCE_QUALITY_ACCEPTABLE_THRESHOLD=0.7500
INTELLIGENCE_QUALITY_REVIEW_THRESHOLD=0.5000
MARKET_REGIME_VERSION=market_regime_v1
MARKET_REGIME_MIN_CONFIDENCE=0.5000
MARKET_REGIME_STRONG_DATA_QUALITY=0.8500
MARKET_REGIME_ACCEPTABLE_DATA_QUALITY=0.6500
HISTORICAL_CASE_VECTOR_VERSION=historical_case_vector_v1
HISTORICAL_CASE_DEFAULT_LIMIT=10
HISTORICAL_CASE_MAX_LIMIT=50
HISTORICAL_CASE_MIN_SCORE=0.5000
DECISION_READINESS_ASSESSMENT_VERSION=decision_readiness_v1
DECISION_READINESS_READY_THRESHOLD=0.8500
DECISION_READINESS_REVIEW_THRESHOLD=0.6500
SCENARIO_ENSEMBLE_VERSION=v1
SCENARIO_ENSEMBLE_DEFAULT_PROVIDER=mock
SCENARIO_ENSEMBLE_MAX_PROVIDERS=3
SCENARIO_ENSEMBLE_MIN_AGREEMENT_RATIO=0.6000
SCENARIO_OUTCOME_EVALUATION_VERSION=v1
SCENARIO_OUTCOME_DEFAULT_HORIZON_MINUTES=30
SCENARIO_OUTCOME_SUPPORT_THRESHOLD=0.6000
EXPLANATION_COMPARISON_VERSION=v1
EXPLANATION_COMPARISON_ALIGNMENT_THRESHOLD=0.7500
EXPLANATION_COMPARISON_REVIEW_THRESHOLD=0.5000
BACKTEST_EXPERIMENT_VERSION=v1
BACKTEST_EXPERIMENT_DEFAULT_LIMIT=100
BACKTEST_EXPERIMENT_MAX_LIMIT=1000
BACKTEST_EXPERIMENT_MINIMUM_SAMPLE_SIZE=20
WALK_FORWARD_VALIDATION_VERSION=v1
WALK_FORWARD_DEFAULT_WINDOW_DAYS=30
WALK_FORWARD_MINIMUM_SAMPLE_SIZE=20
WALK_FORWARD_DEGRADATION_THRESHOLD=0.20
WALK_FORWARD_IMPROVEMENT_THRESHOLD=0.20
COHORT_DRIFT_VERSION=v1
COHORT_DRIFT_MINIMUM_SAMPLE_SIZE=20
COHORT_DRIFT_MILD_THRESHOLD=0.10
COHORT_DRIFT_MODERATE_THRESHOLD=0.20
COHORT_DRIFT_SEVERE_THRESHOLD=0.35
COHORT_DRIFT_DEFAULT_BASELINE_DAYS=90
COHORT_DRIFT_DEFAULT_COMPARISON_DAYS=30
CAPABILITY_REGISTRY_DEFAULT_VERSION=v1
SYNTHETIC_FIXTURES_API_ENABLED=false
SYNTHETIC_FIXTURES_DEFAULT_SEED=12345
MARKET_SESSION_VERSION=v1
MARKET_SESSION_DEFAULT_TIMEZONE=UTC
ADVANCED_FEATURE_PACK_VERSION=v1
ADVANCED_FEATURE_MIN_CANDLE_COUNT=20
ADVANCED_FEATURE_SWING_LOOKBACK=3
ADVANCED_FEATURE_ZONE_LOOKBACK=80
ADVANCED_FEATURE_COMPRESSION_LOOKBACK=20
ADVANCED_FEATURE_EXPANSION_MULTIPLIER=1.5
ADVANCED_FEATURE_WICK_PRESSURE_THRESHOLD=0.55
ADVANCED_FEATURE_MOVEMENT_EFFICIENCY_THRESHOLD=0.60
RULE_PACK_DEFAULT_KEY=default_deterministic_rules
RULE_PACK_DEFAULT_VERSION=v1
REPRODUCIBILITY_MANIFEST_VERSION=v1
EVENT_STUDY_VERSION=v1
EVENT_STUDY_DEFAULT_PRE_EVENT_MINUTES=60
EVENT_STUDY_DEFAULT_POST_EVENT_MINUTES=240
EVENT_STUDY_MIN_CANDLES=5
EVENT_STUDY_STRONG_REACTION_MULTIPLIER=2.0
EVENT_STUDY_MODERATE_REACTION_MULTIPLIER=1.25
CONFIDENCE_CALIBRATION_VERSION=v1
CONFIDENCE_CALIBRATION_DEFAULT_BINS=0-0.39,0.40-0.64,0.65-0.79,0.80-1.0
CONFIDENCE_CALIBRATION_MINIMUM_SAMPLE_SIZE=20
CONFIDENCE_CALIBRATION_OVERCONFIDENT_THRESHOLD=0.15
CONFIDENCE_CALIBRATION_UNDERCONFIDENT_THRESHOLD=0.15
WEBHOOK_OUTBOX_PAYLOAD_VERSION=v1
WEBHOOK_OUTBOX_DEFAULT_STATUS=held
WEBHOOK_OUTBOX_MAX_PAYLOAD_BYTES=32768
OUTCOME_DEFAULT_HORIZONS_MINUTES=5,15,30,60
OUTCOME_MIN_FUTURE_CANDLES=3
OUTCOME_EVALUATION_VERSION=v1
RULE_PACK_DEFAULT_KEY=core_deterministic
RULE_PACK_DEFAULT_VERSION=v1
REPRODUCIBILITY_MANIFEST_VERSION=v1
MARKET_REGIME_VERSION=v1
MARKET_REGIME_MIN_CONFIDENCE=0.50
MARKET_REGIME_STRONG_DATA_QUALITY=0.90
MARKET_REGIME_ACCEPTABLE_DATA_QUALITY=0.75
TIMEFRAME_AGGREGATION_VERSION=v1
TIMEFRAME_AGGREGATION_MIN_COMPLETENESS=1.0
TIMEFRAME_AGGREGATION_ALLOWED_TARGETS=5m,15m,30m,1h,4h
MULTI_TIMEFRAME_CONTEXT_VERSION=v1
CROSS_ASSET_CONTEXT_VERSION=v1
CROSS_ASSET_MIN_CANDLES=20
CROSS_ASSET_MAX_COMPARED_SYMBOLS=20
CROSS_ASSET_LEAD_LAG_MAX_OFFSET=5
CROSS_ASSET_ALIGNMENT_THRESHOLD=0.60
CROSS_ASSET_DIVERGENCE_THRESHOLD=0.60
MARKET_MEMORY_STATE_VERSION=v1
MARKET_MEMORY_FRESH_SECONDS_1M=180
MARKET_MEMORY_FRESH_SECONDS_5M=600
MARKET_MEMORY_FRESH_SECONDS_15M=1800
MARKET_MEMORY_FRESH_SECONDS_1H=7200
MARKET_MEMORY_MAX_CONTEXT_WARNINGS=50
PROFILE_DIAGNOSTICS_MINIMUM_SAMPLE_SIZE=20
PROFILE_DIAGNOSTICS_STRONG_FOLLOW_THROUGH_RATE=0.65
PROFILE_DIAGNOSTICS_HIGH_REVERSAL_RATE=0.35
PROFILE_DIAGNOSTICS_HIGH_NO_FOLLOW_THROUGH_RATE=0.40
PROFILE_DIAGNOSTICS_CONFIDENCE_MISALIGNMENT_THRESHOLD=0.45
PATTERN_ATTRIBUTION_VERSION=v1
PATTERN_ATTRIBUTION_MINIMUM_SAMPLE_SIZE=20
PATTERN_ATTRIBUTION_HIGH_REJECTION_RATE=0.50
PATTERN_ATTRIBUTION_HIGH_REVERSAL_RATE=0.35
PROFILE_GOVERNANCE_DEFAULT_REVIEW_REQUIRED=true
PROFILE_GOVERNANCE_COMPONENT_WEIGHT_TOLERANCE=0.0001
HISTORICAL_CASE_VECTOR_VERSION=v1
HISTORICAL_CASE_DEFAULT_LIMIT=20
HISTORICAL_CASE_MAX_LIMIT=100
HISTORICAL_CASE_MIN_SCORE=0.40
HISTORICAL_CASE_VECTOR_VERSION=v1
HISTORICAL_CASE_DEFAULT_LIMIT=20
HISTORICAL_CASE_MAX_LIMIT=100
HISTORICAL_CASE_MIN_SCORE=0.40
REASONING_ACTION_WORKER_ENABLED=false
REASONING_ACTION_WORKER_POLL_SECONDS=10
REASONING_ACTION_WORKER_BATCH_SIZE=25
REASONING_ACTION_WORKER_MAX_CONCURRENCY=4
REASONING_ACTION_WORKER_LOCK_SECONDS=120
REASONING_ACTION_WORKER_MAX_ATTEMPTS=3
REASONING_ACTION_WORKER_JITTER_SECONDS=2
NOTIFICATION_WORKER_ENABLED=false
NOTIFICATION_WORKER_POLL_SECONDS=10
NOTIFICATION_WORKER_BATCH_SIZE=100
NOTIFICATION_WORKER_LOCK_SECONDS=120
NOTIFICATION_WORKER_MAX_ATTEMPTS=3
NOTIFICATION_WORKER_JITTER_SECONDS=2
MARKET_SCAN_WORKER_ENABLED=false
MARKET_SCAN_WORKER_POLL_SECONDS=30
MARKET_SCAN_WORKER_BATCH_SIZE=10
MARKET_SCAN_DEFAULT_LOOKBACK_MINUTES=60
MARKET_SCAN_DEFAULT_INTERVAL_SECONDS=60
SCANNER_PRESET_VERSION=v1
READ_MODEL_VERSION=v1
READ_MODEL_DEFAULT_LIMIT=200
READ_MODEL_MAX_LIMIT=1000
PROVIDER_POLLING_TIMEOUT_SECONDS=20
PROVIDER_POLLING_MAX_CANDLES_PER_REQUEST=1000
PROVIDER_POLLING_USER_AGENT=trading-intelligence-api-provider-polling/0.1
BINANCE_PUBLIC_REST_BASE_URL=https://api.binance.com
PROVIDER_CREDENTIALS_VERSION=v1
PROVIDER_CREDENTIAL_TEST_TIMEOUT_SECONDS=10
PROVIDER_CREDENTIAL_ALLOW_PUBLIC_TESTS=true
PROVIDER_CREDENTIAL_ALLOW_AUTH_TESTS=false
CANDLE_GAP_RECOVERY_VERSION=v1
CANDLE_GAP_RECOVERY_MAX_GAPS=500
CANDLE_GAP_RECOVERY_MAX_RANGE_DAYS=30
WORKER_SUPERVISOR_COMPONENTS=
WORKER_SUPERVISOR_SHUTDOWN_TIMEOUT_SECONDS=20
RUNTIME_SUPERVISOR_VERSION=v1
RUNTIME_WORKER_STALE_SECONDS=120
RUNTIME_WORKER_HEARTBEAT_ENABLED=true
RUNTIME_SUPERVISOR_RUN_REQUESTS_ENABLED=true
JOB_QUEUE_BACKEND=database
JOB_QUEUE_DEFAULT_MAX_ATTEMPTS=3
JOB_QUEUE_LOCK_SECONDS=300
JOB_QUEUE_CLAIM_BATCH_SIZE=25
JOB_QUEUE_RETRY_BACKOFF_SECONDS=60
JOB_QUEUE_REDIS_URL=
BACKFILL_PLAN_VERSION=v1
PRODUCT_READINESS_VERSION=v1
DEMO_MODE_ENABLED=false
DEMO_MODE_DEFAULT_WORKSPACE_NAME="Demo Workspace"
DEMO_MODE_DEFAULT_SYMBOLS=BTCUSDT,ETHUSDT,EURUSD
DEMO_MODE_DEFAULT_TIMEFRAMES=1m,5m
BACKFILL_PLAN_DEFAULT_LIMIT=1000
BACKFILL_PLAN_MAX_LIMIT=10000
```

`AUTH_MODE=dev` and `AUTH_ENABLED=false` are the local/test defaults. In production, use
`AUTH_MODE=session`, `AUTH_MODE=jwt`, `AUTH_MODE=api_key`, or `AUTH_MODE=mixed`; protected routes resolve an identity
before applying workspace membership and permission checks. For first-party UI login, set `DATABASE_URL`
to a migrated Neon Postgres database, use `AUTH_MODE=session`, and keep `AUTH_PASSWORD_ENABLED=true`.
Password sessions support `/auth/sessions` inventory plus user-owned revoke-one and revoke-other
operations without exposing raw token hashes. Session-authenticated users can rotate their password
with `/auth/password/change`, which verifies the current password, hashes the replacement server-side,
and can revoke other active sessions. Account activity is persisted in `auth_activity_events` and
available through `/auth/activity` with hashed client-host/user-agent correlation fields and no
raw passwords, session tokens, API keys, token hashes, or request bodies.
The legacy `ADMIN_API_KEY` remains supported for compatibility. Health endpoints stay public. Rate limiting is disabled by default,
uses an in-memory fallback for local/test when Redis is not configured, and requires `REDIS_URL`
when enabled in staging or production.

Logs are JSON records with request id, method, path, status code, duration, safe client host, and
error code when applicable. Request bodies, uploaded files, tokens, API keys, database URLs, and
live feed keys are not logged.

Production observability is documented in:

```txt
docs/observability.md
```

Observability endpoints are internal operational monitoring only. They do not send user alerts,
call external monitoring providers by default, execute workers, run analysis, call brokers,
auto-trade, or provide financial advice.

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

Intelligence quality gates and shadow classification are documented in:

```txt
docs/intelligence-quality.md
```

Candle query and quality APIs are documented in:

```txt
docs/candle-query-quality.md
```

Candle/data quality intelligence APIs are documented in:

```txt
docs/data-quality.md
```

Real-time candle gap recovery planning APIs are documented in:

```txt
docs/candle-gap-recovery.md
```

Cross-asset context APIs are documented in:

```txt
docs/cross-asset-context.md
```

Analysis run lifecycle is documented in:

```txt
docs/analysis-run-lifecycle.md
```

Market watchlists and scheduled scans are documented in:

```txt
docs/market-scans.md
```

Signal digest summaries are documented in:

```txt
docs/signal-digests.md
```

Feature engineering snapshots are documented in:

```txt
docs/feature-engineering.md
```

Advanced price-action feature snapshots are documented in:

```txt
docs/advanced-features.md
```

Rule packs and reproducibility manifests are documented in:

```txt
docs/rule-packs.md
```

Event study and news reaction analysis is documented in:

```txt
docs/event-studies.md
```

Confidence calibration curves and reliability tables are documented in:

```txt
docs/confidence-calibration.md
```

Walk-forward validation is documented in:

```txt
docs/walk-forward-validation.md
```

Safe webhook outbox behavior is documented in:

```txt
docs/webhook-outbox.md
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

Multi-timeframe candle aggregation and context are documented in:

```txt
docs/timeframe-aggregation.md
```

Grounded LLM explanations are documented in:

```txt
docs/llm-explanations.md
```

Multi-LLM scenario reasoning is documented in:

```txt
docs/llm-reasoning.md
```

Scenario ensemble consensus diagnostics are documented in:

```txt
docs/scenario-ensembles.md
```

Scenario hypothesis outcome tracking is documented in:

```txt
docs/scenario-outcomes.md
```

Explanation comparison and disagreement analysis is documented in:

```txt
docs/explanation-comparison.md
```

Intelligence capability registry APIs are documented in:

```txt
docs/capabilities.md
```

Backend-safe reasoning action plans are documented in:

```txt
docs/reasoning-action-plans.md
docs/reasoning-action-worker.md
```

Signal outcome evaluation is documented in:

```txt
docs/outcome-evaluation.md
```

Outcome-based profile diagnostics are documented in:

```txt
docs/profile-diagnostics.md
```

Pattern detector attribution diagnostics are documented in:

```txt
docs/pattern-attribution.md
```

Confidence calibration analytics are documented in:

```txt
docs/confidence-calibration.md
```

Strategy profile governance is documented in:

```txt
docs/profile-governance.md
```

Strategy profile simulation sandbox behavior is documented in:

```txt
docs/profile-simulations.md
```

Advanced intelligence operations are documented in:

```txt
docs/data-quality.md
docs/intelligence-datasets.md
docs/market-sessions.md
docs/operator-playbooks.md
```

Historical case retrieval is documented in:

```txt
docs/historical-cases.md
```

Intelligence dataset exports are documented in:

```txt
docs/intelligence-datasets.md
```

Market regime context is documented in:

```txt
docs/market-regimes.md
```

Read-only intelligence reports are documented in:

```txt
docs/intelligence-reports.md
```

Workspace intelligence catalog and search indexing are documented in:

```txt
docs/intelligence-catalog.md
```

Unified analysis context packs are documented in:

```txt
docs/context-packs.md
```

Audit timeline traceability APIs are documented in:

```txt
docs/audit-timeline.md
```

Advanced deterministic context modules are documented in:

```txt
docs/market-regimes.md
docs/historical-cases.md
docs/operator-reviews.md
docs/decision-readiness.md
```

Grounded AI intelligence analyst runs are documented in:

```txt
docs/ai-intelligence.md
```

Internal intelligence metrics are documented in:

```txt
docs/intelligence-metrics.md
```

Intelligence metrics APIs expose internal operational/product counters and optional snapshots. They
do not report trading performance, broker accounting, financial advice, or alerts:

```txt
GET /intelligence-metrics/workspace/{workspace_id}
GET /intelligence-metrics/global
POST /intelligence-metrics/snapshots/workspace/{workspace_id}
POST /intelligence-metrics/snapshots/global
GET /intelligence-metrics/snapshots/latest
GET /intelligence-metrics/snapshots
```

Production service metrics and SLO endpoints are documented in:

```txt
docs/observability.md
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

Intelligence state machine definitions are queryable and can validate lifecycle transitions through:

```txt
GET /state-machines
GET /state-machines/{key}
POST /state-machines/seed-default
POST /state-machines/validate-transition
```

Replay supports `latest_engine_version` and `same_engine_version`. Same-version replay is
supported for the currently registered v1 deterministic engines and returns
`unsupported_engine_version` instead of falling back when a stored snapshot references an
unregistered engine version.

Chart screenshot APIs support manually or externally extracted OHLC rows and deterministic PNG/JPEG
candlestick or OHLC-bar extraction from trading chart images. OCR is optional and provider-backed;
API startup and normal tests do not require Google Vision credentials. Valid extracted rows are
stored through the shared candle path and persisted with a deterministic next-trend hypothesis.
Unsupported non-OHLC screenshots are rejected, and low-confidence extraction requires review or
correction before deterministic analysis can be triggered. Final analysis still runs only from
normalized OHLC candles, never directly from pixels. PNG preview and image ingestion support
request-scoped parser tuning for chart bounds, candle colors, foreground thresholds, and cluster
detection:

```txt
POST /chart-screenshot-runs
POST /chart-screenshot-runs/image/preview
POST /chart-screenshot-runs/image
GET /chart-screenshot-runs
GET /chart-screenshot-runs/{run_id}
POST /chart-screenshot-runs/{run_id}/review
GET /chart-screenshot-runs/{run_id}/decision
GET /chart-screenshot-runs/{run_id}/report
GET /chart-screenshot-runs/{run_id}/lineage
```

Signal outcome evaluation APIs measure observed final-candle behavior after persisted deterministic
signals. They do not calculate broker accounting metrics, produce financial advice, or trigger
execution:

```txt
POST /signals/{signal_id}/outcomes/evaluate
GET /signals/{signal_id}/outcomes
GET /signals/{signal_id}/outcomes/{horizon_minutes}
POST /analysis-runs/{analysis_run_id}/outcomes/evaluate
GET /analysis-runs/{analysis_run_id}/outcomes
POST /outcome-evaluation-runs/backfill
GET /outcome-evaluation-runs/{run_id}
GET /outcomes/performance/patterns
GET /outcomes/performance/strategy-profiles
GET /outcomes/performance/symbols
```

Outcome-based profile diagnostics read stored outcomes and generate advisory calibration
recommendations without auto-changing strategy profiles or classifier thresholds:

```txt
POST /profile-diagnostics/run
GET /profile-diagnostics/runs/{run_id}
GET /profile-diagnostics/strategy-profiles
GET /profile-diagnostics/patterns
GET /profile-diagnostics/recommendations
PATCH /profile-diagnostics/recommendations/{recommendation_id}
```

Confidence calibration APIs compare persisted deterministic confidence scores with observed
follow-through outcomes by bin and horizon. They do not mutate signals, confidence, classifiers, or
strategy profiles:

```txt
POST /confidence-calibration/run
GET /confidence-calibration/runs
GET /confidence-calibration/runs/{run_id}
GET /confidence-calibration/runs/{run_id}/bins
```

Walk-forward validation APIs summarize stored outcome behavior across chronological validation
windows. They do not evaluate missing outcomes, mutate signals, change strategy profiles, advise,
alert, or execute broker workflows:

```txt
POST /walk-forward-validations/run
GET /walk-forward-validations/runs
GET /walk-forward-validations/runs/{run_id}
GET /walk-forward-validations/runs/{run_id}/windows
GET /walk-forward-validations/runs/{run_id}/comparisons
```

Cross-asset context APIs compare stored final candles across related symbols for contextual
alignment, co-movement, divergence, and possible lead/lag only. They do not infer causation, mutate
signals, advise, alert, or execute broker workflows:

```txt
POST /analysis-runs/{analysis_run_id}/cross-asset-context
GET /analysis-runs/{analysis_run_id}/cross-asset-context
POST /signals/{signal_id}/cross-asset-context
GET /signals/{signal_id}/cross-asset-context
GET /cross-asset-context/runs/{run_id}/results
```

Strategy profile governance APIs create, validate, review, approve, and explicitly promote profile
drafts without auto-tuning or mutating active profiles until promotion:

```txt
POST /strategy-profile-drafts
GET /strategy-profile-drafts
GET /strategy-profile-drafts/{draft_id}
PATCH /strategy-profile-drafts/{draft_id}
POST /strategy-profile-drafts/{draft_id}/validate
POST /strategy-profile-drafts/{draft_id}/submit
POST /strategy-profile-drafts/{draft_id}/approve
POST /strategy-profile-drafts/{draft_id}/reject
POST /strategy-profile-drafts/{draft_id}/promote
POST /strategy-profile-drafts/{draft_id}/archive
GET /strategy-profile-drafts/{draft_id}/events
```

Strategy profile simulations compare a hypothetical config against persisted historical signals,
pattern candidates, and observed outcomes without mutating production profiles or final signals:

```txt
POST /profile-simulations/run
GET /profile-simulations/runs/{run_id}
GET /profile-simulations/runs/{run_id}/results
```

Advanced intelligence operations add read-only and diagnostic operator workflows:

```txt
POST /data-quality/candle-range/run
POST /data-quality/data-sources/{source_id}/run
POST /data-quality/live-subscriptions/{subscription_id}/run
GET /data-quality/runs/{run_id}
GET /data-quality/runs/{run_id}/findings
POST /intelligence-datasets/exports
GET /intelligence-datasets/exports
GET /intelligence-datasets/exports/{export_id}
GET /intelligence-datasets/exports/{export_id}/items
GET /intelligence-datasets/exports/{export_id}/jsonl
POST /analysis-runs/{analysis_run_id}/market-session
GET /analysis-runs/{analysis_run_id}/market-session
POST /signals/{signal_id}/market-session
GET /signals/{signal_id}/market-session
GET /operator-playbooks
GET /operator-playbooks/{key}
POST /operator-playbooks/seed
POST /operator-playbooks/evaluate
GET /operator-playbooks/evaluations
```

Market regime context APIs generate deterministic context metadata from persisted analysis,
feature, indicator, signal, and pattern artifacts. They do not mutate signals, change strategy
profiles, send notifications, execute actions, or provide financial advice:

```txt
POST /analysis-runs/{analysis_run_id}/market-regime
GET /analysis-runs/{analysis_run_id}/market-regime
POST /signals/{signal_id}/market-regime
GET /signals/{signal_id}/market-regime
```

Scenario reasoning APIs generate structured, auditable scenario hypotheses from persisted
deterministic artifacts only. They are manual and do not run automatically during analysis:

```txt
POST /signals/{signal_id}/reasoning/scenarios
GET /signals/{signal_id}/reasoning/runs
GET /signals/{signal_id}/reasoning/scenarios/latest
GET /reasoning/runs/{reasoning_run_id}
```

Scenario ensemble APIs compare multiple grounded scenario reasoning runs across provider/model
requests. They persist diagnostics only and do not create final signals, classify, advise, alert, or
execute:

```txt
POST /signals/{signal_id}/scenario-ensemble
GET /signals/{signal_id}/scenario-ensembles
GET /scenario-ensembles/{ensemble_run_id}
GET /scenario-ensembles/{ensemble_run_id}/items
GET /scenario-ensembles/{ensemble_run_id}/consensus
```

Scenario hypothesis outcome APIs evaluate persisted scenario hypotheses against later stored signal
outcomes. They do not generate reasoning, call LLMs, inspect candles directly, mutate hypotheses,
signals, or outcomes, advise, alert, or execute:

```txt
POST /reasoning/scenarios/{scenario_hypothesis_id}/outcome
POST /reasoning/runs/{reasoning_run_id}/scenario-outcomes
GET /reasoning/runs/{reasoning_run_id}/scenario-outcomes
POST /scenario-outcomes/summary
GET /scenario-outcomes/summary/{summary_run_id}
```

Explanation comparison APIs compare persisted deterministic explanations, LLM explanations,
scenario reasoning, and scenario ensemble context for review intelligence only. They do not call
LLM providers, generate explanations, mutate signals, advise, alert, or execute:

```txt
POST /signals/{signal_id}/explanation-comparison
GET /signals/{signal_id}/explanation-comparison/latest
GET /explanation-comparisons/{run_id}
GET /explanation-comparisons/{run_id}/findings
```

Reasoning action plan APIs convert persisted scenario suggestions into bounded backend-safe
follow-up items and can manually execute due deterministic work:

```txt
POST /reasoning/runs/{reasoning_run_id}/action-plan
GET /reasoning/runs/{reasoning_run_id}/action-plan
GET /action-plans/{action_plan_id}
GET /action-plans/{action_plan_id}/items
POST /action-items/{action_item_id}/execute
POST /action-items/mark-due
POST /action-items/execute-due
GET /action-items/due
GET /action-items/worker/status
```

Intelligence report APIs compose persisted artifacts into future UI/operator payloads. They are
read-only and do not run analysis, replay, diagnostics, outcome evaluation, LLM generation, action
execution, alerts, or broker workflows:

```txt
GET /intelligence-reports/signals/{signal_id}
GET /intelligence-reports/analysis-runs/{analysis_run_id}
GET /intelligence-reports/reasoning-runs/{reasoning_run_id}
GET /intelligence-reports/outcomes/{outcome_id}
GET /intelligence-reports/signals/{signal_id}/outcomes
GET /intelligence-reports/screenshot-decisions/{decision_id}
```

Context pack APIs compose persisted artifacts into bounded redacted source-of-truth bundles for
downstream backend modules. They are read-only and do not mutate signals, trigger LLM calls, run
replay, evaluate outcomes, execute action items, call providers, send alerts, or provide financial
advice:

```txt
GET /context-packs/signals/{signal_id}
GET /context-packs/analysis-runs/{analysis_run_id}
GET /context-packs/reasoning-runs/{reasoning_run_id}
GET /context-packs/outcomes/{outcome_id}
GET /context-packs/chart-screenshot-runs/{run_id}
```

Audit timeline APIs compose persisted artifacts into chronological traceability views with artifact
graphs, missing-section reporting, bounded metadata, and deterministic completeness scores. They are
read-only and do not run analysis, replay, diagnostics, outcome evaluation, reasoning, LLM
generation, action execution, alerts, or broker workflows:

```txt
GET /audit-timeline/analysis-runs/{analysis_run_id}
GET /audit-timeline/signals/{signal_id}
GET /audit-timeline/reasoning-runs/{reasoning_run_id}
GET /audit-timeline/action-plans/{action_plan_id}
GET /audit-timeline/outcomes/{outcome_id}
GET /audit-timeline/chart-screenshot-runs/{run_id}
```

AI intelligence APIs generate persisted advisory insight cards from cited backend artifacts. They do
not classify signals, override deterministic outputs, mutate strategy profiles, create executable
action items, send alerts, or perform broker/order/position work:

```txt
POST /ai-intelligence/signals/{signal_id}/analyze
GET /ai-intelligence/runs/{run_id}
GET /ai-intelligence/signals/{signal_id}/runs
```

Workspace intelligence catalog APIs index bounded metadata for persisted intelligence artifacts and
provide workspace-scoped search/filtering without an external search engine or raw payload storage:

```txt
POST /intelligence-catalog/index
POST /intelligence-catalog/reindex
POST /intelligence-catalog/items
DELETE /intelligence-catalog/items
GET /intelligence-catalog/search
GET /intelligence-catalog/items/{item_id}
GET /intelligence-catalog/by-artifact
```

Historical case APIs build deterministic case vectors and search similar past cases for comparable
context and observed outcomes:

```txt
POST /signals/{signal_id}/historical-case-vector
GET /signals/{signal_id}/historical-case-vector
POST /signals/{signal_id}/historical-cases/search
POST /analysis-runs/{analysis_run_id}/historical-cases/search
POST /historical-cases/backfill
```

Intelligence dataset APIs package bounded, redacted JSON and JSONL-ready records from persisted
intelligence artifacts:

```txt
POST /intelligence-datasets/exports
GET /intelligence-datasets/exports
GET /intelligence-datasets/exports/{export_id}
GET /intelligence-datasets/exports/{export_id}/items
GET /intelligence-datasets/exports/{export_id}/jsonl
```

Advanced price-action feature APIs generate deterministic context from final candles only. They do
not mutate existing signals, classify final signal behavior, run LLMs, send alerts, or provide
financial advice:

```txt
POST /analysis-runs/{analysis_run_id}/advanced-features
GET /analysis-runs/{analysis_run_id}/advanced-features
POST /signals/{signal_id}/advanced-features
GET /signals/{signal_id}/advanced-features
```

Rule pack and reproducibility manifest APIs persist deterministic engine provenance for replay,
audit, and reportability:

```txt
POST /rule-packs
GET /rule-packs
GET /rule-packs/{key}/{version}
POST /rule-packs/seed-default
POST /analysis-runs/{analysis_run_id}/reproducibility-manifest
GET /analysis-runs/{analysis_run_id}/reproducibility-manifest
POST /signals/{signal_id}/reproducibility-manifest
GET /signals/{signal_id}/reproducibility-manifest
```

Event study APIs describe observed reactions around stored news events. They do not claim causation
and do not modify news correlation or signal classification:

```txt
POST /event-studies/run
GET /event-studies/runs/{run_id}
GET /event-studies/runs/{run_id}/results
GET /news-events/{news_event_id}/event-studies
```

Confidence calibration APIs summarize reliability alignment from stored outcomes. They do not train
models, adjust strategy profiles, or mutate confidence scores:

```txt
POST /confidence-calibration/run
GET /confidence-calibration/runs
GET /confidence-calibration/runs/{run_id}
GET /confidence-calibration/runs/{run_id}/bins
```

Webhook outbox APIs persist held backend events for future delivery infrastructure. This merge does
not deliver webhooks, require delivery secrets, or expose unsafe LLM output:

```txt
POST /webhook-subscriptions
GET /webhook-subscriptions
GET /webhook-subscriptions/{subscription_id}
PATCH /webhook-subscriptions/{subscription_id}
POST /webhook-subscriptions/{subscription_id}/archive
POST /webhook-outbox/events
GET /webhook-outbox/events
GET /webhook-outbox/events/{event_id}
POST /webhook-outbox/events/{event_id}/cancel
```

Notification APIs persist safe operator-facing outbox messages, user preferences, in-app delivery
state, and worker dispatch state. Notification delivery engine APIs add sanitized backend
intelligence events, provider-configured channels, dedupe, quiet hours, severity routing, delivery
attempts, and an explicit webhook HTTP POST path gated by `NOTIFICATIONS_ENABLED=true`.
Email, Telegram, and Discord adapters are safe stubs in this phase. No notification path sends
trade instructions, creates broker actions, auto-trades, or provides financial advice:

```txt
PUT /notifications/preferences
POST /notifications
GET /notifications
POST /notifications/dispatch-due
GET /notifications/worker/status
POST /notification-channels
GET /notification-channels
GET /notification-channels/{channel_id}
PATCH /notification-channels/{channel_id}
POST /notification-channels/{channel_id}/archive
POST /notification-events
GET /notification-events
GET /notification-events/{event_id}
POST /notification-events/{event_id}/read
POST /notification-events/{event_id}/acknowledge
POST /notification-events/{event_id}/archive
POST /notification-events/{event_id}/deliver
GET /notification-events/{event_id}/attempts
```

`notification_events` also carry in-product inbox state: `unread`, `read`, `acknowledged`,
and `archived`. These fields make sanitized backend intelligence events reviewable inside the
web app without invoking external delivery. Supported inbox event types are signal classification,
review recommendation, outcome evaluation, digest creation, data-quality degradation, stale market
memory, due reasoning action, blocked readiness, opened operator review, completed scan, degraded
provider health, and needed gap recovery. Inbox copy must stay non-advisory and must not become
external signal delivery or broker workflow language.

Multi-timeframe aggregation APIs derive complete higher-timeframe candles from final lower-timeframe
candles, store lineage, and build context without changing existing signal classifications:

```txt
POST /timeframe-aggregation/runs
GET /timeframe-aggregation/runs/{run_id}
GET /timeframe-aggregation/runs
GET /timeframe-aggregation/derived-candles/{candle_id}/lineage
POST /analysis-runs/{analysis_run_id}/multi-timeframe-context
GET /analysis-runs/{analysis_run_id}/multi-timeframe-context
POST /signals/{signal_id}/multi-timeframe-context
GET /signals/{signal_id}/multi-timeframe-context
```

Notification behavior is documented in:

```txt
docs/notifications.md
docs/data-retention.md
```

Data quality intelligence APIs persist deterministic source and candle integrity audits:

```txt
POST /data-quality/candle-range/run
POST /data-quality/data-sources/{source_id}/run
POST /data-quality/live-subscriptions/{subscription_id}/run
GET /data-quality/runs/{run_id}
GET /data-quality/runs/{run_id}/findings
```

They do not predict markets, classify signals, provide financial advice, create alerts, execute
broker actions, mutate analysis results, or change candle final/partial storage behavior.

Engine execution registry behavior is documented in:

```txt
docs/engine-executions.md
```

Engine execution APIs track backend intelligence operation requests, idempotency, lifecycle status,
produced artifacts, errors, attempts, and worker-ready lock fields. They do not run tasks
automatically and are not broker, order, position, auto-trading, alerting, or financial-advice
workflows:

```txt
POST /engine-executions
GET /engine-executions
GET /engine-executions/{record_id}
GET /engine-executions/{record_id}/events
POST /engine-executions/{record_id}/cancel
```

Backfill plan APIs create bounded dry-run contracts for missing or stale derived intelligence
artifacts. They do not execute work automatically, mutate source artifacts, call external providers,
send notifications, or perform broker/order/position work:

```txt
POST /backfill-plans
GET /backfill-plans
GET /backfill-plans/{plan_id}
GET /backfill-plans/{plan_id}/items
POST /backfill-plans/{plan_id}/cancel
```

Backfill planning is documented in:

```txt
docs/backfill-plans.md
```

Disposable database validation, integration fixtures, and smoke commands are documented in:

```txt
docs/integration-tests.md
```

Data contract registry and JSONB artifact validation are documented in:

```txt
docs/data-contracts.md
```

The intelligence state machine registry is documented in:

```txt
docs/state-machines.md
```

Intelligence artifact dependency graph and invalidation behavior is documented in:

```txt
docs/artifact-graph.md
```

Event study reaction analysis is documented in:

```txt
docs/event-studies.md
```

Event study APIs measure deterministic pre-event and post-event final-candle behavior around
persisted news or economic events. They do not claim causation, mutate signals, create alerts, call
LLMs, execute broker actions, or produce financial advice:

```txt
POST /event-studies/run
GET /event-studies/runs/{run_id}
GET /event-studies/runs/{run_id}/results
GET /news-events/{news_event_id}/event-studies
```

Event study settings:

```txt
EVENT_STUDY_VERSION=v1
EVENT_STUDY_DEFAULT_PRE_EVENT_MINUTES=30
EVENT_STUDY_DEFAULT_POST_EVENT_MINUTES=60
EVENT_STUDY_MIN_CANDLES=5
EVENT_STUDY_STRONG_REACTION_MULTIPLIER=2.0
EVENT_STUDY_MODERATE_REACTION_MULTIPLIER=1.25
```

Rule packs and reproducibility manifests are documented in:

```txt
docs/rule-packs.md
```

Rule pack APIs register deterministic version bundles without changing active strategy profile
behavior:

```txt
POST /rule-packs
GET /rule-packs
GET /rule-packs/{key}/{version}
POST /rule-packs/seed-default
```

Reproducibility manifest APIs snapshot existing persisted analysis and signal provenance. They do
not run replay, mutate historical outputs, classify with LLMs, send alerts, or perform broker work:

```txt
POST /analysis-runs/{analysis_run_id}/reproducibility-manifest
GET /analysis-runs/{analysis_run_id}/reproducibility-manifest
POST /signals/{signal_id}/reproducibility-manifest
GET /signals/{signal_id}/reproducibility-manifest
```

Decision readiness assessment is documented in:

```txt
docs/decision-readiness.md
```

Operator playbook policies are documented in:

```txt
docs/operator-playbooks.md
```

Decision readiness APIs assess whether persisted backend artifacts have enough deterministic
support and traceability for operator consumption. They do not classify signals, mutate artifacts,
run replay, evaluate outcomes, execute action items, send alerts, or provide financial advice:

```txt
POST /decision-readiness/signals/{signal_id}/assess
GET /decision-readiness/signals/{signal_id}/latest
POST /decision-readiness/analysis-runs/{analysis_run_id}/assess
GET /decision-readiness/analysis-runs/{analysis_run_id}/latest
GET /decision-readiness
```

Operator playbook APIs map persisted backend states to deterministic operator-safe workflow
recommendations. They do not execute actions, create alerts, send notifications, mutate strategy
profiles, or provide trading advice:

```txt
GET /operator-playbooks
GET /operator-playbooks/{key}
POST /operator-playbooks/seed
POST /operator-playbooks/evaluate
GET /operator-playbooks/evaluations
```

Operator review queue behavior is documented in:

```txt
docs/operator-reviews.md
```

Market session context behavior is documented in:

```txt
docs/market-sessions.md
```

Market session APIs persist deterministic session context for analysis runs and signals:

```txt
POST /analysis-runs/{analysis_run_id}/market-session
GET /analysis-runs/{analysis_run_id}/market-session
POST /signals/{signal_id}/market-session
GET /signals/{signal_id}/market-session
```

Operator review APIs persist human review workflow state and audit events:

```txt
POST /operator-reviews
GET /operator-reviews
GET /operator-reviews/{review_item_id}
POST /operator-reviews/{review_item_id}/assign
POST /operator-reviews/{review_item_id}/status
POST /operator-reviews/{review_item_id}/resolve
POST /operator-reviews/{review_item_id}/dismiss
GET /operator-reviews/{review_item_id}/events
```

Signal digest APIs persist read-only daily, session, custom-period, and watchlist summaries:

```txt
POST /signal-digests
GET /signal-digests
GET /signal-digests/{digest_id}
GET /signal-digests/{digest_id}/items
POST /signal-digests/daily
POST /signal-digests/session
```

They use safe digest language such as bullish bias, bearish bias, no directional signal, setup
quality, review recommended, watch condition, stale data, conflict, observed follow-through, and
observed reversal. They do not send notifications or provide financial advice.
## Webhook Outbox

Webhook outbox APIs persist sanitized integration payload records without sending HTTP requests:

```txt
POST /webhook-subscriptions
GET /webhook-subscriptions
GET /webhook-subscriptions/{subscription_id}
PATCH /webhook-subscriptions/{subscription_id}
POST /webhook-subscriptions/{subscription_id}/archive
POST /webhook-outbox/events
GET /webhook-outbox/events
GET /webhook-outbox/events/{event_id}
POST /webhook-outbox/events/{event_id}/cancel
```

Webhook outbox behavior is documented in:

```txt
docs/webhook-outbox.md
```
## Safety Policy Engine

The API includes a backend-only Safety Policy Engine under `app/modules/safety_policies`.
It provides reusable evaluation and redaction helpers for blocked trading actions, unsafe direct phrases, causation claims, prohibited output claims, provider payload exposure, and public response sanitization.

Default policy set: `core_market_intelligence` version `v1`.

Routes:

- `GET /safety-policies`
- `GET /safety-policies/{key}/{version}`
- `POST /safety-policies/seed-default`
- `POST /safety-policies/evaluate-text`
- `POST /safety-policies/evaluate-action`
- `POST /safety-policies/evaluate-payload`

The engine is additive. Existing explanation, reasoning, reports, datasets, webhook outbox, playbook, and readiness logic can adopt `SafetyPolicyService` incrementally without enabling broker execution, auto-trading, copy trading, alerts, notifications, UI changes, or financial advice.
