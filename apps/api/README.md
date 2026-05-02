# Trading Intelligence API

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
consensus diagnostics, supports replay from
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

No UI, broker execution, auto-trading, alerts, or billing is implemented in this backend slice.
LLM layers are optional and may only explain or reason from persisted deterministic output.
Market regime context is deterministic metadata only and does not alter signal classification.

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

Run the market scan worker:

```sh
MARKET_SCAN_WORKER_ENABLED=true .venv/bin/python -m app.workers.market_scan_worker
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
DATA_QUALITY_VERSION=v1
DATA_QUALITY_STRONG_THRESHOLD=0.95
DATA_QUALITY_ACCEPTABLE_THRESHOLD=0.85
DATA_QUALITY_DEGRADED_THRESHOLD=0.70
DATA_QUALITY_OUTLIER_RANGE_MULTIPLIER=4.0
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
MARKET_SESSION_VERSION=v1
MARKET_SESSION_DEFAULT_TIMEZONE=UTC
OUTCOME_DEFAULT_HORIZONS_MINUTES=5,15,30,60
OUTCOME_MIN_FUTURE_CANDLES=3
OUTCOME_EVALUATION_VERSION=v1
MARKET_REGIME_VERSION=v1
MARKET_REGIME_MIN_CONFIDENCE=0.50
MARKET_REGIME_STRONG_DATA_QUALITY=0.90
MARKET_REGIME_ACCEPTABLE_DATA_QUALITY=0.75
TIMEFRAME_AGGREGATION_VERSION=v1
TIMEFRAME_AGGREGATION_MIN_COMPLETENESS=1.0
TIMEFRAME_AGGREGATION_ALLOWED_TARGETS=5m,15m,30m,1h,4h
MULTI_TIMEFRAME_CONTEXT_VERSION=v1
PROFILE_DIAGNOSTICS_MINIMUM_SAMPLE_SIZE=20
PROFILE_DIAGNOSTICS_STRONG_FOLLOW_THROUGH_RATE=0.65
PROFILE_DIAGNOSTICS_HIGH_REVERSAL_RATE=0.35
PROFILE_DIAGNOSTICS_HIGH_NO_FOLLOW_THROUGH_RATE=0.40
PROFILE_DIAGNOSTICS_CONFIDENCE_MISALIGNMENT_THRESHOLD=0.45
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
PROVIDER_POLLING_TIMEOUT_SECONDS=20
PROVIDER_POLLING_MAX_CANDLES_PER_REQUEST=1000
PROVIDER_POLLING_USER_AGENT=trading-intelligence-api-provider-polling/0.1
BINANCE_PUBLIC_REST_BASE_URL=https://api.binance.com
WORKER_SUPERVISOR_COMPONENTS=
WORKER_SUPERVISOR_SHUTDOWN_TIMEOUT_SECONDS=20
BACKFILL_PLAN_VERSION=v1
BACKFILL_PLAN_DEFAULT_LIMIT=1000
BACKFILL_PLAN_MAX_LIMIT=10000
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

Analysis run lifecycle is documented in:

```txt
docs/analysis-run-lifecycle.md
```

Market watchlists and scheduled scans are documented in:

```txt
docs/market-scans.md
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
