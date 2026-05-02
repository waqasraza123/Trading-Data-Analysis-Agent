# Project State

## Product

This repository is for an AI Trading Intelligence Agent backend. The planned product is a market intelligence engine, not a chatbot, UI, broker integration, or auto-trading system. It must support both CSV/imported historical candle data and live market data feed ingestion. Both ingestion paths must normalize into the same candle storage model and feed the same deterministic analysis engine.

## Current Architecture

- Git repository uses local branch `main` tracking `origin/main`.
- Phase 1 backend foundation exists under `apps/api/`.
- The backend uses FastAPI, Python 3.12+ packaging metadata, Pydantic v2 settings, async SQLAlchemy 2.x, asyncpg, Alembic, pytest, Ruff, and mypy.
- The API currently exposes health, workspace/user setup, symbol configuration, data source configuration, historical candle import, live feed ingestion foundation, candle query/quality, analysis run lifecycle and versioned replay, feature snapshot, indicator snapshot, pattern candidate, strategy profile, engine version, deterministic signal classification, deterministic explanation, deterministic news/event correlation, grounded LLM explanation, signal outcome evaluation, outcome-based profile diagnostics, multi-LLM scenario reasoning, backend-safe reasoning action plans with scheduled due execution, notification outbox/preference endpoints, backend-only market watchlist and scheduled scan endpoints, chart screenshot trend-prediction endpoints, read-only intelligence report endpoints, read-only audit timeline traceability endpoints, grounded AI intelligence analyst endpoints, and deterministic intelligence quality gate/shadow classification endpoints.
- Phase 2 core database schema models and migration exist under `apps/api/`.
- The shared candle validation and normalization layer exists under `apps/api/app/modules/candles/`.
- The live feed ingestion foundation exists under `apps/api/app/modules/live/`.
- Backend operational hardening now includes production-safe settings validation, configurable CORS, optional API key guard, request limits, Redis-backed rate limits, structured request logs, readiness/liveness/Redis/worker health routes, standalone worker entrypoints, and an optional supervised multi-worker process entrypoint.
- The analysis run lifecycle exists under `apps/api/app/modules/analysis/`.
- Deterministic feature engineering exists under `apps/api/app/modules/features/`.
- Deterministic indicator calculation exists under `apps/api/app/modules/indicators/`.
- Deterministic pattern candidate detection exists under `apps/api/app/modules/patterns/`.
- Signal outcome evaluation exists under `apps/api/app/modules/outcomes/`.
- Outcome-based strategy profile and pattern diagnostics exist under `apps/api/app/modules/profile_diagnostics/`.
- The durable backend roadmap is documented in `docs/backend-only-implementation-plan.md`.
- The Phase 0 backend architecture plan is documented in `docs/backend-phase-0-architecture-plan.md`.
- Durable project memory lives in this file.
- Local session memory lives in `docs/_local/current-session.md` and is intentionally ignored by Git.

## Non-Negotiable Rules

- Read `AGENTS.md`, then this file, before implementation decisions.
- Read `docs/_local/current-session.md` if it exists before starting work.
- Do not invent architecture before the first product slice establishes it.
- Follow `docs/backend-only-implementation-plan.md` for backend scope and build order unless a later durable decision supersedes it.
- Backend scope is FastAPI + Neon PostgreSQL first; no UI, broker execution, copy trading, social trading, or financial-advice output in the initial backend.
- CSV, JSON import, API polling, and live feed ingestion must converge through one candle validation/normalization/storage path.
- Live feed candles must track partial vs final state; analysis uses final candles by default and includes partial candles only when explicitly requested.
- Deterministic engines calculate and classify; AI/LLMs may explain only supplied evidence and must never classify or override signals.
- Store intermediate artifacts for audit/replay once implementation begins.
- Do not store secrets in repository memory or local session memory.
- Keep durable state concise, factual, and grounded in repository files.
- Follow repository conventions once they exist; until then, choose conservative, minimal conventions for the first implementation slice.
- Code must be production-grade, strongly typed, validated, modular, testable, and scalable.
- Do not add comments in code; use descriptive and consistent names instead.
- Avoid hardcoded values, hacks, tightly coupled logic, and shortcuts.
- State assumptions explicitly when requirements are missing.
- Keep commit messages under 140 characters and commit/push completed work when requested.

## Current Roadmap

- Build the backend only, following the phase order in `docs/backend-only-implementation-plan.md`.
- Use `docs/backend-only-implementation-plan.md` as the phase-by-phase roadmap.
- Phase 1 FastAPI + Neon foundation is implemented.
- Phase 2 core database schema is implemented for workspaces, users, symbols, data_sources, import_batches, import_errors, candles, live_feed_subscriptions, live_feed_events, analysis_runs, analysis_audit_logs, and engine_versions.
- Phase 3 symbol and data source configuration services are implemented.
- Unified candle validation and normalization is implemented as an internal service layer.
- Historical CSV/JSON import pipeline wiring is implemented.
- Live feed ingestion foundation is implemented with provider adapters, subscription lifecycle APIs, raw event audit storage, stale checks, and shared candle normalization.
- Candle query and data quality APIs are implemented.
- Analysis run lifecycle is implemented with historical/live-window run creation, candle preflight, audit logs, retry handling, insufficient-data status, feature snapshot persistence, indicator snapshot persistence, pattern candidate persistence, deterministic signal classification persistence, and deterministic explanation persistence.
- Deterministic feature engineering snapshots are implemented.
- Deterministic indicator snapshots are implemented.
- Deterministic pattern candidates are implemented.
- Deterministic strategy profiles, signal classification, signal evidence, confidence components, risk notes, and golden intelligence tests are implemented.
- Deterministic explanations are implemented on top of persisted signals, evidence, confidence components, risk notes, strategy profile snapshots, feature snapshots, and indicator snapshots.
- Deterministic news/event correlation is implemented on top of manually/imported events and persisted signals. It is contextual only, avoids causation language, and does not override signal classification or confidence.
- Grounded LLM explanations are implemented as an optional layer on top of deterministic explanation artifacts, with mock/OpenAI provider abstraction, safety checks, grounding checks, and deterministic fallback behavior.
- Multi-LLM scenario reasoning is implemented as an optional manual layer on top of persisted deterministic artifacts, with provider-agnostic adapters, bounded grounded inputs, safety checks, grounding checks, fallback persistence, and scenario hypotheses that never classify, override, advise, execute, or predict guaranteed outcomes.
- Backend-safe reasoning action planning is implemented as an optional manual layer that converts persisted scenario suggestions into validated, idempotent, auditable backend follow-up items for outcome evaluation, replay, news correlation, waiting for final candles, human review, or no action.
- Signal outcome evaluation is implemented as a separate truth loop after persisted deterministic signals. It measures observed final-candle follow-through, favorable movement, adverse movement, reversal, insufficient data, and historical behavior by horizon without calculating broker PnL or changing signal classification.
- Outcome-based profile diagnostics are implemented downstream of stored signals and outcomes. They persist profile/pattern diagnostics and advisory calibration recommendations for operator review without auto-changing strategy profiles, classifier thresholds, action plans, or execution behavior.
- Read-only intelligence reports are implemented as a composition layer over persisted deterministic, LLM, reasoning, action-plan, outcome, diagnostics, audit, and screenshot artifacts. They do not mutate signals, run replay, execute actions, evaluate outcomes, run diagnostics, or generate LLM output.
- Read-only audit timelines are implemented as chronological traceability views over persisted analysis, signal, explanation, news, outcome, reasoning, action-plan, replay, chart screenshot, diagnostic, and audit artifacts. They expose artifact graphs, missing-section reporting, redacted/truncated metadata, and deterministic completeness scores without mutating source artifacts or running backend work.
- Grounded AI intelligence analyst runs are implemented downstream of read-only intelligence reports. They persist advisory insight cards and claim-level citations to stored artifacts, but they do not classify signals, override deterministic outputs, create executable action items, mutate strategy profiles, send notifications, or perform broker/order/position work.
- Deterministic intelligence quality gates are implemented downstream of persisted analysis artifacts and signals. They persist quality runs, quality findings, diagnostic shadow classification comparisons, and review recommendations without mutating final signals, selecting candidates, changing strategy profiles, running replay, evaluating outcomes, executing actions, triggering LLM calls, or producing trading advice.
- Operator notifications are implemented as a safe persisted outbox with user preferences, in-app delivery, idempotency, leases, and worker-ready dispatch state. They must not become trading alerts, financial-advice messages, broker workflows, or external delivery without explicit provider configuration and safety controls.
- Market watchlists and scheduled scans are implemented as backend-only orchestration over stored candle data. They create bounded deterministic analysis runs from final candles by default, optionally request existing reasoning/action-plan layers when configured, and do not send alerts/notifications, execute action items, call brokers, fetch external market data, or provide financial advice.
- Later phases add live scanning, deeper external integrations, and performance tuning.
- Chart screenshot ingestion accepts manually or externally extracted OHLC rows and deterministic PNG/JPEG candlestick or OHLC bar image uploads, supports write-free image extraction preview with request-scoped parser tuning, optional Google Vision OCR axis calibration, structured unsupported-chart rejection for non-OHLC charts, low-confidence review-required gating before deterministic analysis, shared candle storage, deterministic trend hypotheses, human review/correction, optional analysis triggering, decision/report/lineage endpoints, and OCR/calibration audit metadata without storing raw image bytes.
- Add tests with the first meaningful code path and keep verification commands current here.
- Update this file when architecture, roadmap, constraints, or important decisions become durable.

## Completed Major Slices

- Initialized Git repository.
- Added repo-driven Codex context system with durable and local memory files.
- Added backend-only implementation plan for the AI Trading Intelligence Agent.
- Added Phase 0 backend architecture plan covering the FastAPI + Neon foundation and unified CSV/live ingestion boundary.
- Implemented Phase 1 FastAPI + Neon backend foundation under `apps/api/`.
- Implemented Phase 2 core SQLAlchemy models, Alembic migration, and schema documentation.
- Implemented Phase 3 symbol and data source schemas, repositories, services, routes, seed payloads, and documentation.
- Implemented shared candle normalization, validation, quality calculation, repository upsert rules, and internal service documentation.
- Implemented historical CSV/JSON import routes, parsing, batch/error persistence, candle storage wiring, and documentation.
- Implemented live feed provider abstraction, mock/Binance normalizers, subscription lifecycle routes, raw live event audit persistence, stale checks, live candle storage wiring, and documentation.
- Implemented candle query, count, latest, quality APIs, final-by-default read policy, warmup/baseline service helpers, and documentation.
- Implemented analysis run lifecycle routes, historical/live-window preflight, data sufficiency handling, retry policy, audit logs, and documentation.
- Implemented feature_snapshots migration/model, deterministic movement/candle-shape/range/volatility/trend feature engines, feature persistence wiring, feature retrieval route, and documentation.
- Implemented indicator_snapshots migration/model, deterministic EMA/RSI/MACD/ATR engines, indicator persistence wiring, indicator retrieval route, and documentation.
- Implemented pattern_candidates migration/model, deterministic rule detectors, pattern persistence wiring, pattern retrieval route, and documentation.
- Implemented strategy_profiles, signals, signal_confidence_components, signal_evidence, and signal_risk_notes migrations/models, default profile seed data, deterministic classifier service, lifecycle integration, retrieval APIs, audit events, documentation, and intelligence tests.
- Implemented deterministic_explanations migration/model, deterministic explanation templates, safety checker, idempotent persistence service, lifecycle/manual classification integration, retrieval/generation APIs, audit events, documentation, and explanation unit tests.
- Implemented news_events and signal_news_correlations migration/models, manual/import JSON event ingestion APIs, deterministic relevance/scoring service, manual correlation APIs, optional include_news_correlation lifecycle hook, cautious risk-note integration, documentation, and tests.
- Implemented llm_explanations migration/model, grounded LLM input builder, prompt, mock/OpenAI provider abstraction, safety and grounding checks, LLM explanation APIs, optional include_ai_explanation lifecycle hook, documentation, and tests.
- Implemented llm_reasoning_runs and scenario_hypotheses persistence, multi-LLM adapter layer, scenario reasoning input/prompt/parser/safety/grounding/service/repository/routes, documentation, and tests.
- Implemented reasoning_action_plans and reasoning_action_items persistence, backend-safe action validation, scenario-to-action planner, due action executor, scheduled reasoning action worker, action plan APIs, audit events, documentation, and unit tests.
- Implemented signal_outcomes and outcome_evaluation_runs migration/models, deterministic outcome calculator, bounded backfill service, signal/analysis outcome APIs, on-demand aggregation APIs for patterns/strategy profiles/symbols, audit events, documentation, and unit tests.
- Implemented strategy_profile_diagnostic_runs, strategy_profile_diagnostics, pattern_outcome_diagnostics, and calibration_recommendations migration/models, deterministic diagnostic calculator, advisory recommender, bounded diagnostic APIs, documentation, and unit tests.
- Implemented chart_screenshot_runs migration/model, chart_screenshot data source type, screenshot-derived candle storage linkage, deterministic trend-hypothesis service, manual/external OHLC APIs, deterministic PNG candlestick extraction preview and persistence APIs with request-scoped parser tuning, human review/correction workflow, optional analysis-run triggering, chart decision response API, chart audit report API, chart correction lineage API, and documentation.
- Implemented read-only intelligence report builder and API contracts for signal, analysis run, reasoning run, outcome, signal outcome, and screenshot decision reports with bounded sections, redaction, missing-section metadata, docs, and unit tests.
- Implemented read-only audit timeline traceability APIs for analysis runs, signals, reasoning runs, action plans, outcomes, and chart screenshot runs with bounded chronological events, artifact graphs, completeness scoring, redaction/truncation, docs, and unit tests.
- Implemented grounded AI intelligence analyst runs, insights, and claims with citation validation, safety checks, mock-provider support, API routes, docs, and unit tests.
- Implemented deterministic intelligence quality gates and shadow classification validation with persisted quality runs, findings, profile comparison results, review recommendations, API routes, docs, and unit tests.
- Implemented notification_preferences, notification_messages, and notification_worker_runs persistence, notification APIs, in-app outbox dispatch, safety checks, idempotency, worker runtime/entrypoint, docs, and unit tests.
- Implemented market_watchlists, market_watchlist_items, scheduled_scan_configs, scheduled_scan_runs, and scheduled_scan_run_items persistence, watchlist/config/run APIs, bounded due scan executor, optional `python -m app.workers.market_scan_worker`, supervisor registration, docs, and unit tests.
- Implemented chart screenshot hardening with Pillow/OpenCV image decoding, Google Vision OCR provider abstraction, axis calibration metadata, candlestick/OHLC bar extraction, line/area unsupported-chart handling, low-confidence review-required gating, docs, and unit tests.
- Integrated chart screenshot hardening, scheduled scans, audit timeline traceability, and intelligence quality gates into one backend surface with settings-backed defaults, read-only scan/screenshot/quality timeline provenance, diagnostic screenshot quality findings, and a single Alembic head.
- Implemented analysis replay metadata/API for latest-engine deterministic replay, golden intelligence fixture structure, and TEST_DATABASE_URL-gated async DB integration test foundation.
- Implemented workspace/user APIs, idempotent backend seed command/service, engine version registry/query APIs, analysis engine/rule-set snapshots, and current-v1 same-engine replay support.
- Implemented disposable DB validation hardening, backend integration smoke coverage, and a safe `python -m app.cli smoke` command for read-only or explicit write checks against non-production databases.
- Implemented backend security and observability hardening: settings validation, CORS configuration, optional API key guard, request/upload limits, rate-limit foundation, request duration logs, safe error responses with request IDs, health/readiness/worker health endpoints, live worker/stale monitor process hardening, operational docs, and env examples.
- Implemented production Redis-backed rate limiting with local/test in-memory fallback, staging/production Redis configuration validation, Redis health checks, operational docs, and unit coverage.
- Implemented production worker supervisor orchestration for live feed, stale monitor, reasoning action, and notification runtimes with component selection, graceful shutdown, fail-fast child monitoring, docs, and unit tests.

## Important Decisions

- `docs/project-state.md` is committed durable memory and should describe long-lived project facts.
- `docs/_local/current-session.md` is local scratch memory and should not be committed.
- The initial product direction is backend-only: FastAPI controls workflow, Neon stores truth, deterministic engines calculate/classify, and AI only explains.
- The candle table is the planned source-of-truth model for both imported historical data and live-originated data.
- `candles` enforces final/partial candle state through `is_final`; analysis must default to final candles only.
- `candles` enforces one row per workspace, symbol, source, timeframe, and timestamp.
- Repository coding standards are durable: no code comments, strong typing, validation everywhere, modular files, explicit assumptions, and short commit messages.
- Phase 1 intentionally keeps `DATABASE_URL` optional at app startup so local health can run without secrets; `/health/db` reports unhealthy until a database URL is configured.
- Async SQLAlchemy normalizes `postgresql://` and `postgres://` URLs to `postgresql+asyncpg://` for Neon compatibility, and translates Neon pooler `sslmode`/`channel_binding` query parameters into asyncpg-compatible SSL settings.
- Phase 2 owns the first business schema; Phase 3 should add services/routes without changing the ingestion truth boundary.
- Symbol and data source services are the first business configuration APIs; they do not perform imports, live ingestion, or analysis.
- Candle normalization accepts future CSV, JSON, API polling, live feed, and manual seed origins through one `NormalizedCandleInput` path.
- Existing final candles are not overwritten by later partial candles or conflicting final candles.
- Historical imports must use the shared candle normalization and repository path; they do not bypass candle validation.
- CSV imports require `csv_upload` sources; JSON imports require `json_import` sources.
- Live subscriptions require `websocket_live` data sources and supported provider adapters.
- Live provider messages are persisted as `live_feed_events` before candle processing, and provider workers should call the same live ingestion service boundary.
- The current Binance adapter normalizes kline payloads only; persistent websocket lifecycle remains a later worker slice.
- Candle read APIs default to final candles; partial candles are returned only when `is_final=false` or inspected through quality reporting.
- Future analysis code should use `CandleService` read helpers instead of querying candle models directly.
- Analysis run `completed` currently means lifecycle preflight, deterministic feature snapshot, deterministic indicator snapshot, deterministic pattern candidates, deterministic signal classification, and deterministic explanation generation completed.
- Analysis preflight writes audit logs and marks runs `insufficient_data` when candle windows lack required final candles.
- Feature snapshots serialize Decimal market values as strings in JSONB to preserve precision.
- Indicator snapshots serialize Decimal market values as strings in JSONB and use `isReady` flags instead of guessing when warmup/baseline data is thin.
- Pattern candidates serialize Decimal market values as strings in JSONB and mark a selected candidate only when the strongest score clears the deterministic selection threshold.
- Analysis retry replaces prior pattern candidate rows for the same analysis run until a future analysis-attempt model exists.
- Strategy profiles are deterministic market-reading configurations for signal classification; they are not broker strategies, trade execution, auto-trading, or financial advice.
- Optional LLM explanations must remain downstream of deterministic artifacts and must not classify, override signals, invent news, claim causation, or provide trade instructions.
- Optional LLM scenario reasoning must remain manual by default, downstream of deterministic artifacts, and limited to scenario monitoring language plus backend-safe follow-up actions.
- Intelligence reports must remain read-only operator/UI payloads composed from existing persisted artifacts. They must not become a persistence system, classifier, replay runner, diagnostics runner, outcome evaluator, action executor, alert system, broker workflow, or LLM generation path.
- Audit timelines must remain read-only traceability payloads composed from existing persisted artifacts. They must not mutate source artifacts, run analysis, run replay, evaluate outcomes, run scenario reasoning, execute action items, send alerts, perform broker workflows, or provide financial advice.
- AI intelligence analyst outputs must remain advisory and citation-backed. They may identify inconsistencies, uncertainty, missing data, diagnostic context, risk context, and safe investigation steps, but they must not become deterministic truth, signal classification, strategy auto-tuning, action execution, alerts, broker execution, or financial advice.
- Intelligence quality gates and shadow classification are diagnostic-only validation layers. They may persist findings and review recommendations, but they must not mutate signals, mark pattern candidates selected, change strategy profiles, run replay, evaluate outcomes, execute action items, call LLM providers, create alerts, or perform broker/order/position work.
- Notifications are operator-facing backend messages only. Current dispatch supports in-app persistence; email and webhook are modeled as future channels but fail closed as not configured until explicit provider integrations exist.
- Reasoning action plans may persist and execute only backend-safe follow-up work. Trading actions such as buy, sell, enter, exit, order placement, leverage, position management, copy trading, or trade execution are rejected and never persisted as executable items.
- Due reasoning action execution is operational through a separate scheduled worker and the shared `POST /action-items/execute-due` API path. It claims items with database leases, executes only backend-safe deterministic work, records worker runs, skips replay-of-replay by default, and leaves human review pending for a person or future review workflow.
- Outcome evaluation is downstream of persisted signals and final candles only. It evaluates observed historical behavior after classification, does not mutate original signals, does not calculate broker PnL, and does not produce financial advice.
- Profile diagnostics are downstream of persisted signal outcomes only. They use observed behavior, historical follow-through, confidence calibration, evidence quality, and threshold-review terminology; they do not imply guaranteed performance and do not use profit or win-rate language.
- Replay signal outcomes are stored separately for replay signals and must not mutate original signal outcomes.
- Replay runs are stored as normal `analysis_runs` with `analysis_mode='replay'`, `replayed_from_analysis_run_id`, `replay_mode`, `engine_snapshot_json`, and `rule_set_snapshot_json`; `latest_engine_version` uses current registered engines/profiles, and `same_engine_version` supports registered current v1 snapshots or returns `unsupported_engine_version`.
- DB integration tests require explicit `TEST_DATABASE_URL`; unit tests must not fall back to production Neon `DATABASE_URL`.
- Golden integration tests assert deterministic signal outputs and deterministic explanations for completed analysis runs.
- Integration tests migrate and truncate only the explicit `TEST_DATABASE_URL` database and refuse to run when it equals `DATABASE_URL` under production-like `APP_ENV` or `ENV`.
- The smoke CLI defaults to `TEST_DATABASE_URL`, skips writes unless `--include-write-tests` is passed, refuses unsafe production-like `TEST_DATABASE_URL`/`DATABASE_URL` reuse, and refuses write checks under production-like `APP_ENV` or `ENV`.
- `AUTH_ENABLED=false` remains the local/test default; when enabled, mutating routes require the configured API key header while health/readiness routes stay public.
- Rate limiting is disabled by default; local/test can use the in-memory fallback, while staging/production require `REDIS_URL` when rate limiting is enabled and return a stable backend-unavailable error if Redis cannot be reached.
- API readiness requires database connectivity and critical configuration, but does not require the live worker to be running.
- Worker process entrypoints are `python -m app.workers.live_feed_worker`, `python -m app.workers.live_stale_monitor`, `python -m app.workers.reasoning_actions_worker`, `python -m app.workers.notification_worker`, `python -m app.workers.market_scan_worker`, and optional orchestrator `python -m app.workers.supervisor`.
- Chart screenshot OCR uses Google Vision through Application Default Credentials only when `CHART_OCR_ENABLED=true`; manual calibration remains supported and raw uploaded image bytes are not persisted.
- Chart screenshot deterministic analysis can run only from normalized OHLC candles. Non-OHLC chart types are not converted into synthetic candles, and low extraction/OCR confidence requires accepted human review or correction before analysis triggering.
- Audit timeline defaults are settings-backed and remain read-only; timeline routes may include persisted scheduled scan provenance, chart screenshot provenance, quality findings, and shadow classifications, but they must not run or mutate those systems.

## Deferred / Not Yet Implemented

- Lockfile.
- Full external live provider websocket integrations beyond the current runtime/provider foundation.
- Historical engine code execution beyond registered current-v1 replay, news, and scanner modules.
- External API integrations beyond current live provider adapters.
- Deployment configuration beyond the API Dockerfile, CI workflow, and operational docs/env examples.
- Chart screenshot support is hardened for candlestick/OHLC bar images; broader non-OHLC chart families remain unsupported for analysis by design.

## Risks / Watchouts

- The repository name implies trading/financial functionality, but no code currently defines scope, data sources, or risk controls.
- Financial data integrations may require API keys; keep all secrets out of committed and local memory docs.
- Future trading-related features should avoid implying financial advice unless the product explicitly defines compliant behavior.
- Phase 1 set initial backend conventions; later phases should preserve the small-file modular structure under `apps/api/app/`.
- Do not start with `candles -> GPT -> answer`; the durable plan requires deterministic intelligence first and AI explanations second.
- Do not delay the signal/evidence/confidence/risk layer behind optional AI language, news, UI, scanner, or deployment polish.

## Standard Verification

- `git status --short`
- `cd apps/api && python3 -m venv .venv`
- `cd apps/api && .venv/bin/python -m pip install -e ".[dev]"`
- `cd apps/api && .venv/bin/ruff check .`
- `cd apps/api && .venv/bin/mypy app`
- `cd apps/api && .venv/bin/pytest`
- `cd apps/api && TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/pytest -m integration`
- `cd apps/api && TEST_DATABASE_URL=postgresql://user:password@localhost:5432/trading_test .venv/bin/python -m app.cli smoke`
- `cd apps/api && .venv/bin/alembic history`
- `cd apps/api && .venv/bin/uvicorn app.main:app --reload`
