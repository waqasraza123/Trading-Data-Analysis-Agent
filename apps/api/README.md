# Trading Intelligence API

FastAPI backend for deterministic market intelligence over imported and live-originated
candle data. The backend stores market data, calculates features and indicators, classifies
signals with rules, generates safe deterministic and optional grounded LLM explanations from
persisted artifacts, supports optional multi-LLM grounded scenario reasoning, supports replay from
stored candles, persists deterministic news/event context, evaluates observed historical outcomes
after persisted signals, stores outcome-based profile diagnostics and advisory calibration
recommendations, converts persisted reasoning scenarios into backend-safe follow-up action plans,
and composes read-only intelligence reports from existing persisted artifacts. It also accepts
manually or externally extracted trading chart screenshot candles and persists deterministic
next-trend hypotheses. A read-only audit timeline API composes persisted artifacts into
chronological traceability and lineage views for operator review.

No UI, broker execution, auto-trading, alerts, or billing is implemented in this backend slice.
LLM layers are optional and may only explain or reason from persisted deterministic output.

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
symbols, default workspace data sources including manual news context, strategy profiles,
and current engine versions.
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
```

`/health` and `/health/live` only prove the API process is alive. `/health/db` checks
database connectivity. `/health/ready` requires database connectivity and valid critical
configuration. `/health/workers` reports live worker and stale monitor state when a database is
configured, and returns a safe degraded status otherwise.

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

Run a supervised worker process:

```sh
WORKER_SUPERVISOR_COMPONENTS=live_feed,stale_monitor,reasoning_actions,notifications \
REASONING_ACTION_WORKER_ENABLED=true \
NOTIFICATION_WORKER_ENABLED=true \
.venv/bin/python -m app.workers.supervisor
```

Security and traffic controls are configured through environment variables:

```txt
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
CORS_ALLOW_CREDENTIALS=false
AUTH_ENABLED=false
ADMIN_API_KEY=
API_KEY_HEADER_NAME=x-admin-api-key
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
OUTCOME_DEFAULT_HORIZONS_MINUTES=5,15,30,60
OUTCOME_MIN_FUTURE_CANDLES=3
OUTCOME_EVALUATION_VERSION=v1
PROFILE_DIAGNOSTICS_MINIMUM_SAMPLE_SIZE=20
PROFILE_DIAGNOSTICS_STRONG_FOLLOW_THROUGH_RATE=0.65
PROFILE_DIAGNOSTICS_HIGH_REVERSAL_RATE=0.35
PROFILE_DIAGNOSTICS_HIGH_NO_FOLLOW_THROUGH_RATE=0.40
PROFILE_DIAGNOSTICS_CONFIDENCE_MISALIGNMENT_THRESHOLD=0.45
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
WORKER_SUPERVISOR_COMPONENTS=
WORKER_SUPERVISOR_SHUTDOWN_TIMEOUT_SECONDS=20
```

`AUTH_ENABLED=false` is the local/test default. When enabled, mutating routes require the
configured API key header; health/readiness endpoints stay public. Rate limiting is disabled by
default, uses an in-memory fallback for local/test when Redis is not configured, and requires
`REDIS_URL` when enabled in staging or production.

Logs are JSON records with request id, method, path, status code, duration, safe client host, and
error code when applicable. Request bodies, uploaded files, tokens, API keys, database URLs, and
live feed keys are not logged.

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

Deterministic news/event correlation is documented in:

```txt
docs/news-event-correlation.md
```

Chart screenshot trend prediction is documented in:

```txt
docs/chart-screenshot-prediction.md
```

Grounded LLM explanations are documented in:

```txt
docs/llm-explanations.md
```

Multi-LLM scenario reasoning is documented in:

```txt
docs/llm-reasoning.md
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

Read-only intelligence reports are documented in:

```txt
docs/intelligence-reports.md
```

Audit timeline traceability APIs are documented in:

```txt
docs/audit-timeline.md
```

Grounded AI intelligence analyst runs are documented in:

```txt
docs/ai-intelligence.md
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

Replay supports `latest_engine_version` and `same_engine_version`. Same-version replay is
supported for the currently registered v1 deterministic engines and returns
`unsupported_engine_version` instead of falling back when a stored snapshot references an
unregistered engine version.

Chart screenshot APIs support manually or externally extracted OHLC rows and deterministic PNG
candlestick extraction from trading chart images. Valid extracted rows are stored through the shared
candle path and persisted with a deterministic next-trend hypothesis. Both create endpoints can
optionally trigger the existing deterministic analysis lifecycle after extraction. PNG preview and
image ingestion support request-scoped parser tuning for chart bounds, candle colors, foreground
thresholds, and cluster detection:

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

Scenario reasoning APIs generate structured, auditable scenario hypotheses from persisted
deterministic artifacts only. They are manual and do not run automatically during analysis:

```txt
POST /signals/{signal_id}/reasoning/scenarios
GET /signals/{signal_id}/reasoning/runs
GET /signals/{signal_id}/reasoning/scenarios/latest
GET /reasoning/runs/{reasoning_run_id}
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

Notification APIs persist safe operator-facing outbox messages, user preferences, in-app delivery
state, and worker dispatch state. They do not send trade instructions, create broker actions, or
deliver external email/webhook messages yet:

```txt
PUT /notifications/preferences
POST /notifications
GET /notifications
POST /notifications/dispatch-due
GET /notifications/worker/status
```

Notification behavior is documented in:

```txt
docs/notifications.md
```

Disposable database validation, integration fixtures, and smoke commands are documented in:

```txt
docs/integration-tests.md
```
