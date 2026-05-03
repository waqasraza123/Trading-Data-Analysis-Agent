# Project State

## Product

This repository is for an AI Trading Intelligence Agent backend. The planned product is a market intelligence engine, not a chatbot, UI, broker integration, or auto-trading system. It must support both CSV/imported historical candle data and live market data feed ingestion. Both ingestion paths must normalize into the same candle storage model and feed the same deterministic analysis engine.

## Current Architecture

- Workspace intelligence catalog metadata indexing and search endpoints exist for cross-artifact discovery without external search infrastructure or raw payload storage.

- Intelligence capability registry metadata exists under `apps/api/app/modules/capabilities/` for backend module discovery, API/contract/artifact references, runtime availability, credential requirements, execution type, and safety level inspection.

- Deterministic synthetic candle fixture generation exists under `apps/api/app/modules/synthetic_fixtures/` for backend development, QA, parser validation, demos, and future golden tests without external data, database persistence, production data mutation, analysis execution, alerts, broker actions, auto-trading, or financial advice.

- A backend-only intelligence state machine registry exists under `apps/api/app/modules/state_machines/` for versioned lifecycle definitions, valid transition inspection, terminal states, optional transition validation, and validation audit records.

- Internal intelligence metrics endpoints and optional database snapshots exist for backend operational/product counters.

- Operator review queue backend exists under `apps/api/app/modules/operator_reviews/` as a backend-only human workflow state layer for intelligence artifacts. It records review items and events only; it does not execute trades, send alerts, call LLMs, mutate signals, accept chart screenshot analysis, or change strategy profiles.
- Market session context backend exists under `apps/api/app/modules/market_sessions/` as a deterministic context layer for analysis runs and signals. It stores rough UTC session labels for audit and later grouping without mutating signal classification, outcomes, diagnostics, or strategy profiles.
- Cross-asset context backend exists under `apps/api/app/modules/cross_asset_context/` as a deterministic final-candle-only layer for correlation, co-movement, divergence, and lead/lag context across related symbols. It does not infer causation, mutate signals, call LLMs, send alerts, execute broker actions, or provide financial advice.

- Git repository uses local branch `main` tracking `origin/main`.
- Phase 1 backend foundation exists under `apps/api/`.
- Bounded backfill plan endpoints exist under `apps/api/app/modules/backfill_plans/` for creating dry-run plan and item records only.
- The backend uses FastAPI, Python 3.12+ packaging metadata, Pydantic v2 settings, async SQLAlchemy 2.x, asyncpg, Alembic, pytest, Ruff, and mypy.
- The API currently exposes health, workspace/user setup, symbol configuration, data source configuration, historical candle import, live feed ingestion foundation, candle query/quality, analysis run lifecycle and versioned replay, feature snapshot, indicator snapshot, pattern candidate, strategy profile, engine version, deterministic signal classification, deterministic explanation, deterministic news/event correlation, grounded LLM explanation, signal outcome evaluation, outcome-based profile diagnostics, multi-LLM scenario reasoning, backend-safe reasoning action plans with scheduled due execution, notification outbox/preference endpoints, backend-only market watchlist and scheduled scan endpoints, chart screenshot trend-prediction endpoints, read-only intelligence report endpoints, read-only audit timeline traceability endpoints, grounded AI intelligence analyst endpoints, and deterministic intelligence quality gate/shadow classification endpoints.
- Phase 2 core database schema models and migration exist under `apps/api/`.
- The shared candle validation and normalization layer exists under `apps/api/app/modules/candles/`.
- The live feed ingestion foundation exists under `apps/api/app/modules/live/`.
- Backend operational hardening now includes production-safe settings validation, configurable CORS, optional API key guard, request limits, Redis-backed rate limits, structured request logs, readiness/liveness/Redis/worker health routes, standalone worker entrypoints, and an optional supervised multi-worker process entrypoint.
- The analysis run lifecycle exists under `apps/api/app/modules/analysis/`.
- Deterministic feature engineering exists under `apps/api/app/modules/features/`.
- Deterministic advanced price-action feature snapshots exist under `apps/api/app/modules/advanced_features/`.
- Rule pack and reproducibility manifest persistence exists under `apps/api/app/modules/rule_packs/`.
- Event study and news reaction analysis exists under `apps/api/app/modules/event_studies/`.
- Confidence calibration curves and reliability table persistence exists under `apps/api/app/modules/confidence_calibration/`.
- Safe webhook outbox persistence exists under `apps/api/app/modules/webhook_outbox/`.
- Deterministic indicator calculation exists under `apps/api/app/modules/indicators/`.
- Deterministic pattern candidate detection exists under `apps/api/app/modules/patterns/`.
- Signal outcome evaluation exists under `apps/api/app/modules/outcomes/`.
- Outcome-based strategy profile and pattern diagnostics exist under `apps/api/app/modules/profile_diagnostics/`.
- Confidence calibration analytics exist under `apps/api/app/modules/confidence_calibration/` as a downstream reliability layer over persisted deterministic signals and outcomes.
- Backtest experiment cohort analysis exists under `apps/api/app/modules/backtest_experiments/`.
- Walk-forward validation exists under `apps/api/app/modules/walk_forward_validation/` as a historical stability layer over stored deterministic signals and outcomes.
- Scenario hypothesis outcome tracking exists under `apps/api/app/modules/scenario_outcomes/` as deterministic reasoning QA over persisted scenario hypotheses and stored signal outcomes.
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
- Market data provider polling is implemented under `apps/api/app/modules/provider_polling/` for backend-only historical/recent OHLC ingestion through `api_polling` data sources and the shared candle normalization/storage path.
- Real-time candle gap recovery planning exists under `apps/api/app/modules/candle_gap_recovery/` as planning metadata for missing final candles and optional pending provider polling request creation without external fetch execution.
- Candle query and data quality APIs are implemented.
- Analysis run lifecycle is implemented with historical/live-window run creation, candle preflight, audit logs, retry handling, insufficient-data status, feature snapshot persistence, indicator snapshot persistence, pattern candidate persistence, deterministic signal classification persistence, and deterministic explanation persistence.
- Deterministic feature engineering snapshots are implemented.
- Deterministic indicator snapshots are implemented.
- Deterministic pattern candidates are implemented.
- Deterministic strategy profiles, signal classification, signal evidence, confidence components, risk notes, and golden intelligence tests are implemented.
- Deterministic explanations are implemented on top of persisted signals, evidence, confidence components, risk notes, strategy profile snapshots, feature snapshots, and indicator snapshots.
- Deterministic news/event correlation is implemented on top of manually/imported events and persisted signals. It is contextual only, avoids causation language, and does not override signal classification or confidence.
- Historical case retrieval is implemented as deterministic JSON similarity over persisted signal, profile, pattern, feature, indicator, news-correlation, outcome, and explanation artifacts. It does not require an external vector database or pgvector and does not predict, advise, alert, or execute.
- Intelligence dataset exports are implemented as bounded, redacted JSON/JSONL-ready packages of persisted deterministic intelligence artifacts for future evaluation, model testing, offline analysis, and QA. They do not train models, upload datasets externally, mutate source artifacts, include secrets/raw images/raw full candle series by default, or provide financial advice.
- Grounded LLM explanations are implemented as an optional layer on top of deterministic explanation artifacts, with mock/OpenAI provider abstraction, safety checks, grounding checks, and deterministic fallback behavior.
- Multi-LLM scenario reasoning is implemented as an optional manual layer on top of persisted deterministic artifacts, with provider-agnostic adapters, bounded grounded inputs, safety checks, grounding checks, fallback persistence, and scenario hypotheses that never classify, override, advise, execute, or predict guaranteed outcomes.
- Backend-safe reasoning action planning is implemented as an optional manual layer that converts persisted scenario suggestions into validated, idempotent, auditable backend follow-up items for outcome evaluation, replay, news correlation, waiting for final candles, human review, or no action.
- Signal outcome evaluation is implemented as a separate truth loop after persisted deterministic signals. It measures observed final-candle follow-through, favorable movement, adverse movement, reversal, insufficient data, and historical behavior by horizon without calculating broker PnL or changing signal classification.
- Outcome-based profile diagnostics are implemented downstream of stored signals and outcomes. They persist profile/pattern diagnostics and advisory calibration recommendations for operator review without auto-changing strategy profiles, classifier thresholds, action plans, or execution behavior.
- Confidence calibration analytics are implemented downstream of stored deterministic signals and outcomes. They persist confidence-bin reliability tables by horizon and optional filters without mutating signals, confidence scores, classifiers, outcomes, strategy profiles, alerts, or execution behavior.
- Walk-forward validation is implemented downstream of stored deterministic signals and outcomes. It persists validation runs, time-window aggregates, and horizon comparisons for observed follow-through, reversal behavior, confidence alignment, stability, degradation, and sample-size coverage without evaluating missing outcomes, mutating signals, changing strategy profiles, sending alerts, executing broker actions, or providing financial advice.
- Scenario hypothesis outcome tracking is implemented downstream of persisted scenario reasoning and stored signal outcomes. It persists support/contradiction/inconclusive labels for scenario hypotheses without generating new reasoning, evaluating candles directly, mutating source artifacts, calling LLMs, alerting, executing broker actions, or providing financial advice.
- Read-only intelligence reports are implemented as a composition layer over persisted deterministic, LLM, reasoning, action-plan, outcome, diagnostics, audit, and screenshot artifacts. They do not mutate signals, run replay, execute actions, evaluate outcomes, run diagnostics, or generate LLM output.
- Read-only audit timelines are implemented as chronological traceability views over persisted analysis, signal, explanation, news, outcome, reasoning, action-plan, replay, chart screenshot, diagnostic, and audit artifacts. They expose artifact graphs, missing-section reporting, redacted/truncated metadata, and deterministic completeness scores without mutating source artifacts or running backend work.
- Grounded AI intelligence analyst runs are implemented downstream of read-only intelligence reports. They persist advisory insight cards and claim-level citations to stored artifacts, but they do not classify signals, override deterministic outputs, create executable action items, mutate strategy profiles, send notifications, or perform broker/order/position work.
- Deterministic intelligence quality gates are implemented downstream of persisted analysis artifacts and signals. They persist quality runs, quality findings, diagnostic shadow classification comparisons, and review recommendations without mutating final signals, selecting candidates, changing strategy profiles, running replay, evaluating outcomes, executing actions, triggering LLM calls, or producing trading advice.
- Explanation comparison is implemented as deterministic review intelligence over persisted deterministic explanations, grounded LLM explanations, scenario reasoning, scenario ensembles, signal evidence, risk notes, and news correlations. It persists alignment runs and findings without calling LLMs, generating explanations, mutating signals/explanations, classifying signals, alerting, executing brokers, or providing financial advice.
- Operator notifications are implemented as a safe persisted outbox with user preferences, in-app delivery, idempotency, leases, and worker-ready dispatch state. They must not become trading alerts, financial-advice messages, broker workflows, or external delivery without explicit provider configuration and safety controls.
- Advanced price-action feature snapshots are implemented as an optional deterministic layer over final candles for impulse, correction, wick pressure, movement efficiency, compression/expansion, swing structure, support/resistance zones, exhaustion risk, and liquidity sweep candidate context. They do not mutate signals, change classification behavior, auto-run broker workflows, send alerts, or provide financial advice.
- Rule packs and reproducibility manifests are audit/provenance artifacts for deterministic replay and reporting. They must not change signal classification behavior unless a future explicit replay path consumes them.
- Event studies describe observed reactions around persisted news events and must not claim causation or modify news correlation, signals, outcomes, or strategy profiles.
- Confidence calibration summarizes historical reliability alignment and must not train models, rewrite confidence scores, or auto-adjust strategy profiles.
- Scenario hypothesis outcome tracking reads stored scenario hypotheses and signal outcomes only. It must not generate scenario reasoning, call LLMs, mutate hypotheses/signals/outcomes, evaluate candles directly, send alerts, execute broker workflows, or provide financial advice.
- Webhook outbox stores held backend events only. This merge does not implement webhook delivery, alerts, target secret management, or external notification dispatch.
- Market watchlists and scheduled scans are implemented as backend-only orchestration over stored candle data. They create bounded deterministic analysis runs from final candles by default, optionally request existing reasoning/action-plan layers when configured, and do not send alerts/notifications, execute action items, call brokers, fetch external market data, or provide financial advice.
- Multi-timeframe candle aggregation is implemented as a deterministic backend layer that derives complete higher-timeframe candles from final lower-timeframe candles, records lineage and completeness, and stores multi-timeframe context without mutating existing signal classifications.
- Later phases add live scanning, deeper external integrations, and performance tuning.
- Chart screenshot ingestion accepts manually or externally extracted OHLC rows and deterministic PNG/JPEG candlestick or OHLC bar image uploads, supports write-free image extraction preview with request-scoped parser tuning, optional Google Vision OCR axis calibration, structured unsupported-chart rejection for non-OHLC charts, low-confidence review-required gating before deterministic analysis, shared candle storage, deterministic trend hypotheses, human review/correction, optional analysis triggering, decision/report/lineage endpoints, and OCR/calibration audit metadata without storing raw image bytes.
- Add tests with the first meaningful code path and keep verification commands current here.
- Update this file when architecture, roadmap, constraints, or important decisions become durable.

## Completed Major Slices

- Implemented workspace intelligence catalog and search index metadata table, indexing service, search APIs, and documentation for cross-artifact discovery.

- Implemented intelligence_capabilities persistence, default capability registry, runtime availability summaries, capability APIs, and documentation.

- Implemented deterministic synthetic candle fixture generator, guarded dev API, stdout-only CLI export helper, CSV/JSON import payload exports, and documentation.

- Implemented intelligence state machine registry persistence, default lifecycle definitions, optional transition validation APIs, and documentation.

- Implemented intelligence_metric_snapshots persistence, reusable intelligence metrics collector/repository/service/routes, missing-module warnings, operational health summary counters, and docs.

- Implemented rule_packs and analysis_reproducibility_manifests persistence, default deterministic rule pack seeding, manifest generation APIs for analysis runs and signals, replay support status checks against the current engine registry, and rule-pack documentation.

- Implemented deterministic candle/data quality intelligence monitor with persisted runs/findings, candle range checks, data source checks, live subscription stale checks, quality labels, analysis-use metadata, API routes, and documentation.

- Implemented `operator_review_items` and `operator_review_events` persistence, operator review APIs, idempotent active-source review creation, optional source adapter helpers, safety boundaries, and docs.
- Implemented `market_session_contexts` persistence, deterministic market-session classifier, analysis-run/signal generation and retrieval APIs, settings, safety boundaries, and docs.

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
- Implemented historical_case_vectors and historical_case_searches migration/models, deterministic case-vector builder, weighted case similarity search, bounded backfill APIs, audit search persistence, documentation, and future reasoning/report helper.
- Implemented intelligence_dataset_exports and intelligence_dataset_export_items migration/models, dataset builder, redaction policy, inline JSON/manifest-only storage modes, JSONL endpoint, documentation, and bounded APIs for signal supervision, outcome evaluation, reasoning grounding, quality review, screenshot review, and mixed intelligence datasets.
- Implemented llm_explanations migration/model, grounded LLM input builder, prompt, mock/OpenAI provider abstraction, safety and grounding checks, LLM explanation APIs, optional include_ai_explanation lifecycle hook, documentation, and tests.
- Implemented llm_reasoning_runs and scenario_hypotheses persistence, multi-LLM adapter layer, scenario reasoning input/prompt/parser/safety/grounding/service/repository/routes, documentation, and tests.
- Implemented reasoning_action_plans and reasoning_action_items persistence, backend-safe action validation, scenario-to-action planner, due action executor, scheduled reasoning action worker, action plan APIs, audit events, documentation, and unit tests.
- Implemented signal_outcomes and outcome_evaluation_runs migration/models, deterministic outcome calculator, bounded backfill service, signal/analysis outcome APIs, on-demand aggregation APIs for patterns/strategy profiles/symbols, audit events, documentation, and unit tests.
- Implemented strategy_profile_diagnostic_runs, strategy_profile_diagnostics, pattern_outcome_diagnostics, and calibration_recommendations migration/models, deterministic diagnostic calculator, advisory recommender, bounded diagnostic APIs, documentation, and unit tests.
- Implemented confidence_calibration_runs and confidence_calibration_bins persistence, confidence-bin reliability calculator, bounded calibration APIs, settings defaults, and documentation.
- Implemented chart_screenshot_runs migration/model, chart_screenshot data source type, screenshot-derived candle storage linkage, deterministic trend-hypothesis service, manual/external OHLC APIs, deterministic PNG candlestick extraction preview and persistence APIs with request-scoped parser tuning, human review/correction workflow, optional analysis-run triggering, chart decision response API, chart audit report API, chart correction lineage API, and documentation.
- Implemented read-only intelligence report builder and API contracts for signal, analysis run, reasoning run, outcome, signal outcome, and screenshot decision reports with bounded sections, redaction, missing-section metadata, docs, and unit tests.
- Implemented read-only audit timeline traceability APIs for analysis runs, signals, reasoning runs, action plans, outcomes, and chart screenshot runs with bounded chronological events, artifact graphs, completeness scoring, redaction/truncation, docs, and unit tests.
- Implemented grounded AI intelligence analyst runs, insights, and claims with citation validation, safety checks, mock-provider support, API routes, docs, and unit tests.
- Implemented deterministic intelligence quality gates and shadow classification validation with persisted quality runs, findings, profile comparison results, review recommendations, API routes, docs, and unit tests.
- Implemented explanation comparison and disagreement analysis with persisted comparison runs/findings, deterministic text/structured artifact checks, alignment scoring, API routes, settings, migration, and docs.
- Implemented notification_preferences, notification_messages, and notification_worker_runs persistence, notification APIs, in-app outbox dispatch, safety checks, idempotency, worker runtime/entrypoint, docs, and unit tests.
- Implemented market_watchlists, market_watchlist_items, scheduled_scan_configs, scheduled_scan_runs, and scheduled_scan_run_items persistence, watchlist/config/run APIs, bounded due scan executor, optional `python -m app.workers.market_scan_worker`, supervisor registration, docs, and unit tests.
- Implemented chart screenshot hardening with Pillow/OpenCV image decoding, Google Vision OCR provider abstraction, axis calibration metadata, candlestick/OHLC bar extraction, line/area unsupported-chart handling, low-confidence review-required gating, docs, and unit tests.
- Implemented advanced_feature_snapshots persistence, deterministic advanced price-action calculator, analysis-run and signal APIs, settings, docs, and migration.
- Integrated rule_packs, analysis_reproducibility_manifests, event_study_runs, event_study_results, confidence_calibration_runs, confidence_calibration_bins, webhook_subscriptions, webhook_outbox_events, and webhook_delivery_attempts into shared settings, route registration, model registration, docs, and Alembic merge metadata.
- Integrated chart screenshot hardening, scheduled scans, audit timeline traceability, and intelligence quality gates into one backend surface with settings-backed defaults, read-only scan/screenshot/quality timeline provenance, diagnostic screenshot quality findings, and a single Alembic head.
- Documented the advanced deterministic context integration contract for market regime context, historical case retrieval, operator reviews, and decision readiness. These modules are backend-only diagnostic/readiness layers and must not mutate signals, auto-apply calibration, execute action items, call brokers, send alerts, or provide financial advice.
- Implemented analysis replay metadata/API for latest-engine deterministic replay, golden intelligence fixture structure, and TEST_DATABASE_URL-gated async DB integration test foundation.
- Implemented workspace/user APIs, idempotent backend seed command/service, engine version registry/query APIs, analysis engine/rule-set snapshots, and current-v1 same-engine replay support.
- Implemented disposable DB validation hardening, backend integration smoke coverage, and a safe `python -m app.cli smoke` command for read-only or explicit write checks against non-production databases.
- Implemented backend security and observability hardening: settings validation, CORS configuration, optional API key guard, request/upload limits, rate-limit foundation, request duration logs, safe error responses with request IDs, health/readiness/worker health endpoints, live worker/stale monitor process hardening, operational docs, and env examples.
- Implemented production Redis-backed rate limiting with local/test in-memory fallback, staging/production Redis configuration validation, Redis health checks, operational docs, and unit coverage.
- Implemented production worker supervisor orchestration for live feed, stale monitor, reasoning action, and notification runtimes with component selection, graceful shutdown, fail-fast child monitoring, docs, and unit tests.
- Implemented data contract schema registry and validation tracking for important backend JSONB artifacts with default v1 contracts, strict/loose validation, source-payload validation support, API routes, migration, docs, and focused validator tests.
- Implemented intelligence backfill plan and item persistence, bounded dry-run planner contracts, missing outcome/context/stale/module plan APIs, safety metadata, docs, and migration.
- Implemented intelligence artifact dependency graph and invalidation infrastructure for artifact registration, dependency paths, stale marking, invalidation events/items, recomputation candidate listing, API routes, docs, and database schema.
- Implemented workspace data retention policy planning with dry-run-first run records, itemized cleanup candidates, safe payload redaction apply flow, and data retention documentation.
- Implemented backtest experiment cohort analysis over existing persisted signals and outcomes with bounded filters, cohort persistence, safe observed behavior metrics, docs, and APIs.
- Implemented walk-forward validation over stored deterministic signals and outcomes with bounded filters, inferred or explicit validation periods, window persistence, horizon comparisons, safe stability/degradation metrics, docs, and APIs.
- Implemented scenario hypothesis outcome tracking over persisted scenario hypotheses and stored signal outcomes with deterministic mapping rules, support labels, summary runs, docs, and APIs.
- Implemented multi-timeframe aggregation and context persistence with derived candle lineage, completion accounting, higher-timeframe agreement scoring, APIs, docs, and settings.
- Integrated multi-timeframe aggregation, strategy profile governance, provider polling, scenario ensembles, and backtest experiments behind one backend route/model/settings/migration surface with a merge migration.
- Implemented real-time candle gap recovery plan and item persistence, final-candle gap detection, provider polling preparation metadata, optional pending provider polling request row creation, APIs, docs, and settings.
- Implemented cross-asset context runs/results, deterministic correlation and lead/lag calculation, analysis-run and signal APIs, settings, docs, and migration.
- Integrated cross-asset context, walk-forward validation, candle gap recovery, explanation comparison, and capability registry behind one route/model/settings/documentation surface with a final Alembic merge migration.

## Important Decisions

- Intelligence catalog rows are workspace-scoped metadata pointers to source artifacts. They store bounded titles, summaries, labels, tags, searchable text, and metadata only; source artifacts remain authoritative and are not mutated by indexing.

- Capability registry rows are global backend metadata records. They describe module existence, contracts, routes, artifacts, dependencies, credentials, execution type, and safety boundaries only; they do not execute modules, mutate intelligence artifacts, start workers, call providers, send alerts, run broker workflows, or provide financial advice.

- Synthetic candle fixtures are generated inputs for development/testing only. They may be exported as candle dictionaries, CSV, or JSON import payloads, but they must not fetch external data, mutate production data, run analysis automatically, create alerts, execute broker workflows, or provide financial advice.

- The state machine registry is additive. It preserves existing status strings and database constraints, does not force existing services to validate transitions yet, and exists for operator inspection plus future service-by-service adoption.

- Intelligence metrics are internal operational counters only. Missing optional metric source tables are recorded as warnings and do not fail collection. They must not become trading performance claims, broker PnL, alerts, external observability, or financial-advice output.

- Rule packs are registry records for deterministic engine versions, strategy profile references, parser/OCR versions, thresholds, module versions, and replay compatibility metadata. They do not change active strategy profiles automatically.
- Reproducibility manifests describe persisted analysis and signal provenance for audit/replay compatibility. They snapshot existing artifacts, do not run replay, do not recalculate artifacts, and do not mutate historical analysis or signal outputs.

- Data quality intelligence persists deterministic candle/source health runs and findings. It reads candles, data sources, and live subscriptions, but does not mutate candle storage, analysis runs, signals, outcomes, alerts, broker execution, or LLM classifications.

- Operator reviews are operator-facing workflow records only. They may point at chart screenshots, signals, analysis runs, reasoning runs, action items, quality findings, calibration recommendations, outcomes, or manual sources, but they must not mutate those sources or become trade approvals, alerts, notifications, broker workflows, copy trading, auto-trading, or financial advice.
- Market session context uses rough UTC windows for forex, classifies crypto as 24/7, and deliberately avoids invented stock/index/commodity exchange hours without an exchange calendar. It is market context only and must not become financial advice, alerts, broker execution, or signal mutation.
- Cross-asset context reads stored final candles only, aligns symbols by timestamp, stores contextual correlation/divergence/lead-lag labels, and must not become causation inference, deterministic signal mutation, trade recommendation, alerting, broker execution, or financial advice.
- The integrated context/diagnostics modules are additive. They may persist contextual records and readiness/report evidence for future consumers, but they must not mutate final signals, auto-trigger provider polling, call LLMs for classification, create alerts, execute broker workflows, claim causation, or provide financial advice.

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
- Provider polling requires `api_polling` sources and supported adapters. It is market-data ingestion only, with no broker execution, order placement, alerts, UI, auto-trading, financial advice, or paid provider key requirement at startup.
- Candle gap recovery is planning-only. It reads final candles, records missing final-candle ranges, can create pending provider polling request rows when explicitly requested, and must not call providers, mutate candles directly, send alerts, execute brokers, auto-trade, or provide financial advice.
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
- Workspace data retention is an operational hygiene layer only. It defaults to dry-run, preserves itemized audit records, prefers payload redaction over deletion, has no automatic worker, and skips unsupported destructive actions.
- Reasoning action plans may persist and execute only backend-safe follow-up work. Trading actions such as buy, sell, enter, exit, order placement, leverage, position management, copy trading, or trade execution are rejected and never persisted as executable items.
- Due reasoning action execution is operational through a separate scheduled worker and the shared `POST /action-items/execute-due` API path. It claims items with database leases, executes only backend-safe deterministic work, records worker runs, skips replay-of-replay by default, and leaves human review pending for a person or future review workflow.
- Outcome evaluation is downstream of persisted signals and final candles only. It evaluates observed historical behavior after classification, does not mutate original signals, does not calculate broker PnL, and does not produce financial advice.
- Historical case retrieval is downstream of persisted deterministic artifacts only. It stores deterministic JSON vectors and bounded search records, does not mutate signals or outcomes, does not require pgvector, and must use similar-case/observed-outcome terminology instead of prediction or advice language.
- Intelligence dataset exports are downstream of persisted artifacts only. They create auditable manifests and redacted records for offline evaluation and QA, not ML training or external upload, and must not include secrets, raw images, raw provider payloads, or raw full candle series by default.
- Profile diagnostics are downstream of persisted signal outcomes only. They use observed behavior, historical follow-through, confidence calibration, evidence quality, and threshold-review terminology; they do not imply guaranteed performance and do not use profit or win-rate language.
- Confidence calibration is reliability analysis only. It compares deterministic confidence bins with observed follow-through outcomes, excludes insufficient data from alignment denominators, reports insufficient data separately, and must not become financial advice, signal mutation, classifier override, profile auto-tuning, alerts, broker execution, auto-trading, or profit-oriented reporting.
- Backtest experiments are downstream of existing persisted signals and outcomes only. They group bounded historical outcome rows into cohorts, never auto-evaluate missing outcomes, never mutate signals or strategy profiles, and never use profit, PnL, win-rate, trading advice, alerts, or broker execution behavior.
- Walk-forward validation is downstream of existing persisted signals and outcomes only. It groups stored outcomes into chronological validation windows, compares sufficient windows by horizon, never auto-evaluates missing outcomes, never mutates signals or strategy profiles, and must use observed follow-through, reversal behavior, confidence alignment, stability, degradation, and sample-size terminology.
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
- Data contract validation is additive and centralizes compatibility checks for JSONB artifacts. It does not replace existing module-owned Pydantic schemas, mutate stored artifacts, classify signals, generate financial advice, or execute actions.
- Backfill plans are planning contracts only. They persist bounded plan/item records for missing or stale derived artifacts, default to dry-run behavior, never run automatically, and must not mutate source artifacts or call external providers.
- Advanced feature snapshots use `CandleService` final-candle reads and persist deterministic context only. They are not trading signals, do not classify buy/sell direction, do not update existing signal classification, and do not use LLMs.
- Reliability modules must use safe terminology: observed reaction, possible relationship, historical follow-through rate, continuation rate, calibration alignment, held outbox event, and deterministic context. Avoid profit, guaranteed, trade advice, causation claims, and webhook alert delivery language.
- Multi-timeframe aggregation only persists complete derived candles, skips incomplete windows, uses a `derived_aggregation` data source, and preserves existing final candle conflict semantics.
- The scalable intelligence engine integration keeps timeframe aggregation, profile governance, provider polling, scenario ensembles, and backtest experiments as backend-only deterministic or diagnostic layers. They may read each other's persisted artifacts through explicit services, but they must not auto-promote profile drafts, mutate final signals, run broker workflows, send alerts, train models, or provide financial advice.
- Audit timeline defaults are settings-backed and remain read-only; timeline routes may include persisted scheduled scan provenance, chart screenshot provenance, quality findings, and shadow classifications, but they must not run or mutate those systems.
- Decision readiness, market regime context, historical case retrieval, and operator reviews are diagnostic context modules. They may read persisted artifacts and store their own records, but they must not classify signals, override deterministic outputs, auto-create downstream work except through explicit APIs, execute action items, or mutate existing analysis artifacts.

## Recent Durable Update

- Market regime context is implemented as a deterministic backend-only layer under `apps/api/app/modules/market_regimes/`.
- `market_regime_contexts` stores trend, volatility, range, data quality, warnings, inputs, confidence, and summary metadata per `analysis_run_id + regime_version`.
- Market regime generation is manual through analysis-run and signal endpoints. It reads persisted analysis, feature, indicator, signal, and pattern artifacts without mutating signals, strategy profiles, outcomes, notifications, chart screenshot modules, or scheduled scan behavior.
- The layer is contextual reporting metadata only and must not become financial advice, signal override, execution, copy trading, alerting, or auto-trading behavior.

## Latest Durable Update

- Market data provider polling is implemented under `apps/api/app/modules/provider_polling/` with `provider_polling_requests` and `provider_polling_errors` persistence.
- Supported v1 adapters are `mock_polling`, `binance_public_rest` public klines, and a safe `generic_ohlc_http` stub for future provider mappings.
- Provider polling normalizes adapter candles into `NormalizedCandleInput` with `api_polling` origin and stores through existing candle validation/repository behavior, so conflicting final candles are not overwritten.
- Provider polling APIs are documented in `apps/api/docs/provider-polling.md` and exposed under `/provider-polling`.
- Decision readiness assessments are implemented under `apps/api/app/modules/decision_readiness/` with persistence in `decision_readiness_assessments`.
- Decision readiness reads already persisted signal, analysis, evidence, confidence, explanation, LLM safety/grounding, news, outcome, reasoning, action-plan, profile-diagnostic, audit, and chart screenshot artifacts.
- Decision readiness is backend intelligence readiness for operator consumption only. It is not trade readiness, buy/sell readiness, execution readiness, profitability assessment, broker workflow, alerting, LLM classification, replay, outcome evaluation, or financial advice.
- Decision readiness APIs are documented in `apps/api/docs/decision-readiness.md` and exposed under `/decision-readiness`.
- Operator playbook policies are implemented under `apps/api/app/modules/operator_playbooks/` with `operator_playbooks` and `operator_playbook_evaluations` persistence.
- Operator playbooks map persisted backend states to safe workflow recommendations only. They do not execute action items, create alerts, send notifications, mutate strategy profiles, call LLMs, perform broker work, or provide financial advice.
- Default operator playbooks cover inconsistent quality, missing evidence, blocked readiness, low follow-through, low-confidence chart extraction, blocked LLM output, and ready-signal no-action states.
- Operator playbook APIs are documented in `apps/api/docs/operator-playbooks.md` and exposed under `/operator-playbooks`.
- Scenario ensemble consensus diagnostics are implemented under `apps/api/app/modules/scenario_ensembles/` with `scenario_ensemble_runs`, `scenario_ensemble_items`, and `scenario_consensus_results` persistence.
- Scenario ensembles run multiple grounded scenario reasoning provider/model requests over the same signal input, store linked reasoning run IDs, exclude unsafe or ungrounded outputs from consensus, and persist scenario-level agreement/disagreement diagnostics.
- Scenario ensembles do not classify signals, override deterministic outputs, create final signals, execute actions, send alerts, call brokers, mutate existing reasoning runs, or provide financial advice.
- Scenario ensemble APIs are documented in `apps/api/docs/scenario-ensembles.md`.

- Intelligence artifact graph records traceability and invalidation state only. It can mark downstream artifacts stale and record invalidation paths, but it does not delete artifacts, recompute artifacts, run tasks, mutate signal classifications, send notifications, execute broker workflows, or produce financial advice.

## Deferred / Not Yet Implemented

- Lockfile.
- Full external live provider websocket integrations beyond the current runtime/provider foundation.
- Automatic data retention cleanup worker.
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

## Event Study Reaction Analysis

- Deterministic event-study reaction analysis is implemented on top of persisted news/economic events and final candle data.
- Event studies store pre-event movement, post-event movement, volatility reaction, direction labels, reaction labels, data-quality labels, and summary metadata.
- Event studies must not claim causation, mutate signals, classify signals, send alerts, call LLMs, execute broker actions, or provide financial advice.
- Event-study APIs are `POST /event-studies/run`, `GET /event-studies/runs/{run_id}`, `GET /event-studies/runs/{run_id}/results`, and `GET /news-events/{news_event_id}/event-studies`.

## Latest Local Update

- Implemented safe webhook outbox records for future integrations with `webhook_subscriptions`, `webhook_outbox_events`, and `webhook_delivery_attempts`.
- Webhook outbox is separate from notifications, does not deliver alerts or HTTP requests, and stores sanitized payloads only.
- Payload redaction excludes secrets, signing secret plaintext, raw images, full candle series, unsafe blocked LLM output, and direct trading-instruction language.

## Latest Durable Update

- Implemented engine execution registry as shared backend intelligence operation tracking with `engine_execution_records`, `engine_execution_events`, service/repository/routes, adapter helpers, idempotency, attempts, produced artifacts, error fields, and worker-ready lock fields.
- Engine execution records do not run tasks automatically and must not become broker, order, position, auto-trading, alerting, or financial-advice workflows.

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

## Latest Durable Update

- Implemented strategy profile simulation sandbox endpoints and persistence for diagnostic what-if review.
- The sandbox compares hypothetical strategy profile config overrides against persisted historical signals, pattern candidates, feature/indicator snapshots, and observed outcomes.
- Simulation artifacts are stored separately in `strategy_profile_simulation_runs` and `strategy_profile_simulation_results`.
- Profile simulations do not mutate `strategy_profiles`, final `signals`, selected pattern candidates, diagnostics, classifier behavior, action plans, notifications, broker execution, auto-trading, copy trading, or financial-advice outputs.
- Documentation lives in `apps/api/docs/profile-simulations.md`.
- Integrated advanced intelligence operations modules for data quality runs/findings, intelligence dataset JSONL exports, market session contexts, and operator playbook evaluations.
- New operation tables are `data_quality_runs`, `data_quality_findings`, `intelligence_dataset_exports`, `intelligence_dataset_export_items`, `market_session_contexts`, `operator_playbooks`, and `operator_playbook_evaluations`.
- These modules are backend-only diagnostic/read-only/operator-review layers and do not execute broker actions, auto-apply recommendations, mutate final signals, send alerts, export secrets/raw images/full candle series by default, or provide financial advice.
# Current Session Addition

- Strategy profile governance is implemented as a manual operator workflow for drafts, deterministic validation, review, approval, explicit promotion, and audit history. Draft approval does not activate a profile, promotion is explicit, older active versions remain active unless `deactivatePrevious=true` is requested, and past signals keep their original strategy profile snapshots.
## Safety Policy Engine

Added a backend-only unified Safety Policy Engine module at `apps/api/app/modules/safety_policies/`.

Durable decisions:

- Default policy set is `core_market_intelligence` version `v1`.
- Policy sets and evaluations are persisted in `safety_policy_sets` and `safety_policy_evaluations`.
- The engine centralizes blocked trading actions, unsafe language, causation review flags, invented evidence review flags, prohibited claims, provider payload exposure checks, secret redaction, and public response sanitization.
- This phase is additive and does not broadly refactor existing deterministic explanations, LLM explanations, reasoning, scenario ensembles, action plans, reports, datasets, webhook outbox, operator playbooks, or decision readiness.
- Future adoption should call `SafetyPolicyService` from low-risk public output and payload paths first, then move toward existing safety checks after parity coverage exists.
## Context Pack Update

- Unified analysis context packs are implemented as a canonical read-only composition layer over persisted signal, analysis run, reasoning run, outcome, chart screenshot, replay, evidence, explanation, audit, quality, decision readiness, report, and optional market-context artifacts.
- Context packs produce bounded, redacted, typed source-of-truth artifact snapshots for downstream backend modules and do not mutate signals, trigger LLM calls, run replay, evaluate outcomes, execute actions, call external providers, send alerts, or provide financial advice.
- Context pack APIs are `GET /context-packs/signals/{signal_id}`, `GET /context-packs/analysis-runs/{analysis_run_id}`, `GET /context-packs/reasoning-runs/{reasoning_run_id}`, `GET /context-packs/outcomes/{outcome_id}`, and `GET /context-packs/chart-screenshot-runs/{run_id}`.
