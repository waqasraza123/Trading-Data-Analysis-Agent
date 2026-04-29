# Project State

## Product

This repository is for an AI Trading Intelligence Agent backend. The planned product is a market intelligence engine, not a chatbot, UI, broker integration, or auto-trading system. It must support both CSV/imported historical candle data and live market data feed ingestion. Both ingestion paths must normalize into the same candle storage model and feed the same deterministic analysis engine.

## Current Architecture

- Git repository uses local branch `main` tracking `origin/main`.
- Phase 1 backend foundation exists under `apps/api/`.
- The backend uses FastAPI, Python 3.12+ packaging metadata, Pydantic v2 settings, async SQLAlchemy 2.x, asyncpg, Alembic, pytest, Ruff, and mypy.
- The API currently exposes health, symbol configuration, data source configuration, historical candle import, live feed ingestion foundation, candle query/quality, analysis run lifecycle, feature snapshot, and indicator snapshot endpoints; no signal classification logic exists yet.
- Phase 2 core database schema models and migration exist under `apps/api/`.
- The shared candle validation and normalization layer exists under `apps/api/app/modules/candles/`.
- The live feed ingestion foundation exists under `apps/api/app/modules/live/`.
- The analysis run lifecycle exists under `apps/api/app/modules/analysis/`.
- Deterministic feature engineering exists under `apps/api/app/modules/features/`.
- Deterministic indicator calculation exists under `apps/api/app/modules/indicators/`.
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
- Analysis run lifecycle is implemented with historical/live-window run creation, candle preflight, audit logs, retry handling, insufficient-data status, feature snapshot persistence, and indicator snapshot persistence.
- Deterministic feature engineering snapshots are implemented.
- Deterministic indicator snapshots are implemented.
- Next phase is pattern candidates.
- Later phases add signal engines, evidence/confidence/risk notes, explanations, news correlation, live scanning, replay/versioning, golden tests, observability, security, and performance tuning.
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

## Important Decisions

- `docs/project-state.md` is committed durable memory and should describe long-lived project facts.
- `docs/_local/current-session.md` is local scratch memory and should not be committed.
- The initial product direction is backend-only: FastAPI controls workflow, Neon stores truth, deterministic engines calculate/classify, and AI only explains.
- The candle table is the planned source-of-truth model for both imported historical data and live-originated data.
- `candles` enforces final/partial candle state through `is_final`; analysis must default to final candles only.
- `candles` enforces one row per workspace, symbol, source, timeframe, and timestamp.
- Repository coding standards are durable: no code comments, strong typing, validation everywhere, modular files, explicit assumptions, and short commit messages.
- Phase 1 intentionally keeps `DATABASE_URL` optional at app startup so local health can run without secrets; `/health/db` reports unhealthy until a database URL is configured.
- Async SQLAlchemy normalizes `postgresql://` and `postgres://` URLs to `postgresql+asyncpg://` for Neon compatibility.
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
- Analysis run `completed` currently means lifecycle preflight, deterministic feature snapshot, and deterministic indicator snapshot completed; pattern/signal engines are not implemented yet.
- Analysis preflight writes audit logs and marks runs `insufficient_data` when candle windows lack required final candles.
- Feature snapshots serialize Decimal market values as strings in JSONB to preserve precision.
- Indicator snapshots serialize Decimal market values as strings in JSONB and use `isReady` flags instead of guessing when warmup/baseline data is thin.

## Deferred / Not Yet Implemented

- README and product usage documentation.
- Lockfile.
- Workspace and user API routes.
- Seed execution command.
- Persistent live provider websocket workers and reconnect loops.
- Pattern candidates.
- Signal, evidence, confidence, risk note, explanation, news, replay, and scanner modules.
- Background workers, storage orchestration, and external API integrations.
- Deployment configuration beyond the API Dockerfile and CI workflow.

## Risks / Watchouts

- The repository name implies trading/financial functionality, but no code currently defines scope, data sources, or risk controls.
- Financial data integrations may require API keys; keep all secrets out of committed and local memory docs.
- Future trading-related features should avoid implying financial advice unless the product explicitly defines compliant behavior.
- Phase 1 set initial backend conventions; later phases should preserve the small-file modular structure under `apps/api/app/`.
- Do not start with `candles -> GPT -> answer`; the durable plan requires deterministic intelligence first and AI explanations second.

## Standard Verification

- `git status --short`
- `cd apps/api && python3 -m venv .venv`
- `cd apps/api && .venv/bin/python -m pip install -e ".[dev]"`
- `cd apps/api && .venv/bin/ruff check .`
- `cd apps/api && .venv/bin/mypy app`
- `cd apps/api && .venv/bin/pytest`
- `cd apps/api && .venv/bin/alembic history`
- `cd apps/api && .venv/bin/uvicorn app.main:app --reload`
