# Current Session

## Equity Data Operation Recovery Plan

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added backend recovery plans for equity data operations:
  - `GET /equity-data/operations/{operation_id}/recovery-plan` composes safe operator next steps
    from operation status, diagnostics, retry readiness, row errors, and optional review context;
  - plans include overall status, recommended action, retry/stop availability, blockers, warnings,
    and ordered steps for diagnostics review, attention review, optional stop, optional retry,
    retry-blocker resolution, and row-error review;
  - audit bundles now include the recovery plan and a recovery-plan section summary;
  - the endpoint is read-only and does not create operations, enqueue jobs, retry work, cancel work,
    claim jobs, call providers, mutate artifacts, expose secrets, or provide financial advice.
- Added web recovery plan composition:
  - shared API client function and typed recovery plan/step contracts;
  - selected operation audit bundle panel now shows the recovery recommendation and top ordered
    steps before retry readiness, lineage, diagnostics, and row errors.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Retry Readiness

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added backend retry readiness for equity data operations:
  - `GET /equity-data/operations/{operation_id}/retry-readiness` reports whether a warning,
    failed, or cancelled operation can be retried from persisted context;
  - readiness checks retryable status, replayable payload availability, workspace match, compacted
    row payload blockers, provider credential readiness, requested run mode, sync feasibility,
    replay source, row count, blockers, and warnings;
  - audit bundles now include retry readiness and a retry-readiness section summary;
  - the endpoint is read-only and does not create operations, enqueue jobs, retry work, cancel work,
    call providers for market data, mutate artifacts, expose secrets, or provide financial advice.
- Added web retry readiness composition:
  - shared API client function and typed readiness contract;
  - selected operation audit bundle panel now shows ready/blocked state, replay source, row count,
    requested mode, blockers, and warnings before the diagnostic timeline.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Audit Bundle

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added backend operation audit bundles for equity data operations:
  - `GET /equity-data/operations/{operation_id}/audit-bundle` composes selected operation detail,
    recent row errors, diagnostics, retry lineage, optional review-queue context, and bounded audit
    section summaries;
  - query controls include `error_limit`, `scan_limit`, and `stale_after_minutes`;
  - the bundle is read-only and does not retry, cancel, enqueue, claim jobs, execute workers, call
    providers, expose secrets, mutate artifacts, or provide financial advice.
- Added web audit bundle composition:
  - shared API client function and typed bundle/section contracts;
  - `selectedOperationAuditBundle` on `EquityResearchData`;
  - selected operation detail now hydrates from the bundle and shows bundle section health before
    request/result summaries, diagnostics, retry lineage, and row errors.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Retry Lineage

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added backend retry lineage for equity data operations:
  - `GET /equity-data/operations/{operation_id}/lineage` returns the selected operation, root
    operation, source chain, downstream retry attempts, and a bounded lineage tree;
  - lineage is derived from persisted `retryOfOperationId` and `retryReason` request-summary
    metadata created by guarded retry operations;
  - the endpoint scans recent workspace operations up to `scan_limit` for siblings/descendants and
    fetches direct source ancestors by id when present;
  - it is read-only and does not create retry records, enqueue jobs, execute work, cancel work, call
    providers, expose secrets, mutate artifacts, or provide financial advice.
- Added web lineage composition:
  - shared API client function and typed lineage contracts;
  - `selectedOperationLineage` on `EquityResearchData`;
  - selected operation detail now shows source count, retry count, root operation, retry reasons,
    status, creation time, and links to open related operation details.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Review Queue

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added a backend operation review queue for equity data operations:
  - `GET /equity-data/operations/review-queue` returns failed, warning, cancelled, and stale
    pending/running operations for a workspace;
  - each item includes review reason, severity, safe recommended action, retry eligibility, stop
    eligibility, stale threshold, and last update timestamp;
  - stale detection is read-only through `stale_after_minutes` and does not claim jobs, retry work,
    cancel work, enqueue work, call providers, expose provider secrets, or mutate artifacts.
- Added web review queue composition:
  - shared API client function and typed review queue contracts;
  - `operationReviewQueue` on `EquityResearchData`;
  - `EquityDataOperationsPanel` now shows a bounded operation review queue with review links and
    backend-provided safe action text.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/repository.py apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Diagnostics

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added backend operation diagnostics for equity data operations:
  - `GET /equity-data/operations/{operation_id}/diagnostics` composes the operation, linked job
    queue item, job events, linked provider request, recent import errors, and chronological
    timeline entries;
  - timeline entries are derived from existing operation, job, provider request, and import-error
    records and do not create new events or mutate source artifacts;
  - missing linked job rows are tolerated so older or manually adjusted operations still return a
    diagnostics payload;
  - the endpoint does not claim jobs, retry work, cancel work, call providers, expose provider
    secrets, execute broker workflows, send alerts, or provide financial advice.
- Added web diagnostics composition:
  - shared API client function and typed diagnostics contracts;
  - `selectedOperationDiagnostics` on `EquityResearchData`;
  - selected operation detail now shows linked job status, provider request status, and a bounded
    diagnostic timeline.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Retry Controls

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added guarded backend retry support for equity data operations:
  - `POST /equity-data/operations/{operation_id}/retry` accepts optional `runMode`,
    `idempotencyKey`, and `reason`;
  - only `completed_with_warnings`, `failed`, and `cancelled` operations are retryable;
  - retry creates a new operation from replayable persisted request payloads and leaves the source
    operation unchanged as audit history;
  - compacted or oversized row payload summaries are rejected with typed errors instead of creating
    unusable retry jobs;
  - retry preserves credential readiness checks and does not roll back prior artifacts, restore
    cancelled jobs, call brokers, send alerts, or provide financial advice.
- Added web retry composition:
  - `retryEquityDataOperation` in the shared equity data API client;
  - typed retry input contract;
  - retry buttons and row-level success/error messages in `EquityDataOperationsPanel`.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py apps/api/app/modules/equity_data/schemas.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Summary

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added backend operation summary support for equity data operations:
  - `GET /equity-data/operations/summary` returns total, active, terminal, warning, failed, and
    cancelled counts;
  - grouped status, operation type, and provider counts are exposed for cockpit health review;
  - a bounded recent problem-operation list surfaces warning/failed/cancelled operations without
    claiming jobs, retrying work, calling providers, or mutating artifacts.
- Added web operation summary composition:
  - `getEquityDataOperationSummary` in the shared equity data client;
  - `operationSummary` on `EquityResearchData`;
  - summary cards and recent problem-operation review links in `EquityDataOperationsPanel`.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/repository.py apps/api/app/modules/equity_data/schemas.py apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Detail Review

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added selected operation detail review to the equity research surface:
  - `/equity-research` now accepts `operationId`;
  - shared equity data API client now loads `GET /equity-data/operations/{operation_id}`;
  - typed operation detail and import-error contracts were added in the web equity data types;
  - `EquityDataOperationsPanel` now links each row to a server-loaded detail view with counters,
    request/result summaries, linked job/provider context, cancellation reasons, and recent row
    import errors.
- Updated docs and durable memory:
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Controls UI

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added frontend operation stop controls for the equity research data surface:
  - shared API client function for `POST /equity-data/operations/{operation_id}/cancel`;
  - typed cancellation payload contract;
  - `EquityDataOperationsPanel` now shows Stop controls for pending/running operations only;
  - row-level pending/error messaging, route refresh after stop requests, and linked job/provider
    request context are visible in operation rows;
  - cancellation copy stays operational and non-advisory.
- Updated docs and durable memory:
  - `apps/web/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## Equity Data Operation Idempotency And Cancellation

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Implemented production-grade equity data operation control:
  - JSON operation submissions now reuse an existing operation when `idempotencyKey`, workspace,
    operation type, provider, and dry-run mode match;
  - conflicting reuse of an idempotency key now returns a typed conflict instead of creating
    ambiguous duplicate operation records;
  - `POST /equity-data/operations/{operation_id}/cancel` cancels non-terminal operations and linked
    job queue items in the same transaction when present;
  - running enrichment and earnings-to-catalyst operations now check cancellation between item-level
    steps and stop cooperatively without rewriting already persisted audit artifacts.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/README.md`;
  - `apps/web/docs/equity-data.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - `python3 -m py_compile apps/api/app/modules/equity_data/repository.py apps/api/app/modules/equity_data/schemas.py apps/api/app/modules/equity_data/operations.py apps/api/app/modules/equity_data/routes.py` passed;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## First-Party Auth Activity Audit

- Current worktree was clean before this task; no pending work needed a pre-implementation commit.
- Added first-party auth activity persistence:
  - `auth_activity_events` SQLAlchemy model and Alembic migration;
  - bounded event/status enums for register, login, logout, password change, session revocation, and API-key administration;
  - hashed email, client-host, and user-agent correlation values without storing raw passwords, bearer tokens, API keys, request bodies, IP addresses, or user agents;
  - request ID, identity source, error code, and bounded metadata fields for operational traceability.
- Added backend audit recording for:
  - register/login success and known `AppError` failures;
  - logout success;
  - session revoke-one and revoke-other success;
  - password change success;
  - API-key create/revoke success.
- Added `GET /auth/activity` for session-authenticated users to list recent activity for their own user/workspace.
- Updated web account data loading and `/account` UI to show recent activity alongside password change and session inventory controls.
- Updated docs and durable memory:
  - `apps/api/docs/auth.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passes;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## First-Party Password Rotation

- Current worktree was clean before this task; no pending work needed a pre-implementation commit.
- Added authenticated first-party password rotation:
  - `POST /auth/password/change` requires a session-authenticated user;
  - verifies the current password before hashing the replacement with the existing PBKDF2-SHA256 helper;
  - rejects unchanged passwords;
  - clears failed-attempt lock state after valid current-password verification;
  - optionally revokes other active sessions while keeping the current bearer session.
- Added `/account` password-change UI:
  - current/new/confirm password fields;
  - default-on option to revoke other active sessions;
  - shared account API client call through the existing same-origin session proxy path.
- Updated RBAC route-coverage policy for auth self-service exemptions:
  - register/login/logout;
  - password change;
  - session revoke-one/revoke-other.
- Updated docs and durable memory:
  - `apps/api/docs/auth.md`;
  - `apps/api/docs/rbac-route-coverage.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passes;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## First-Party Session Management

- Committed and pushed the existing session-memory update first:
  - commit `eeec520` (`Update session memory`) on `main`.
- Implemented production-grade first-party session management:
  - backend `GET /auth/sessions` with bounded user-owned session inventory;
  - backend `POST /auth/sessions/{session_id}/revoke` for one owned session;
  - backend `POST /auth/sessions/revoke-other` for revoking other active owned sessions while preserving the current bearer token;
  - response schemas avoid raw token/token-hash exposure and mark the current session from the bearer token hash;
  - expired active sessions are normalized to `expired` during inventory/revocation operations.
- Added web `/account` route with:
  - server-side session-cookie-aware account data fetch;
  - identity/workspace/session metrics;
  - session table with current-session sign-out and other-session revocation controls;
  - route loading skeleton and shared navigation/auth-status links.
- Updated docs and durable memory:
  - `apps/api/docs/auth.md`;
  - `apps/api/README.md`;
  - `apps/web/README.md`;
  - `apps/web/docs/motion-ui.md`;
  - `apps/web/scripts/motion-rollout-manifest.json`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passes;
  - safe-language scan over changed auth/account docs and code found only existing safety-boundary language;
  - no tests, lint runs, typechecks, or builds were run per user instruction.

## First-Party Auth UI And Sessions

- Added first-party password registration/login/logout to the FastAPI auth module:
  - `auth_password_credentials` stores PBKDF2-SHA256 password hashes;
  - `auth_sessions` stores hashed bearer session tokens with expiry/revocation state;
  - `POST /auth/register`, `POST /auth/login`, and `POST /auth/logout` issue/revoke sessions;
  - `AUTH_MODE=session` and mixed-mode session resolution are supported.
- Added Alembic revision `202605101200_password_auth` for Neon/Postgres-compatible auth tables.
- Added Next.js `/login` and `/register` UI, same-origin auth route handlers, HttpOnly session cookie storage,
  middleware gating for `NEXT_PUBLIC_AUTH_MODE=session`, and auth status/sign-out controls in app navigation.
- Updated web/backend env examples and auth docs for Neon/Postgres session mode.
- Verification:
  - `cd apps/api && .venv/bin/pytest app/tests/unit/test_auth.py app/tests/test_config.py -q` passes;
  - `cd apps/api && .venv/bin/ruff check app/modules/auth app/db/models.py app/tests/unit/test_auth.py app/tests/conftest.py app/config.py alembic/versions/202605101200_add_password_auth_sessions.py` passes;
  - `cd apps/api && .venv/bin/ruff format --check app/modules/auth app/db/models.py app/tests/unit/test_auth.py app/tests/conftest.py app/config.py alembic/versions/202605101200_add_password_auth_sessions.py` passes;
  - `cd apps/api && .venv/bin/alembic heads` reports `202605101200_password_auth`;
  - `cd apps/api && .venv/bin/python -c "from app.main import create_app; from app.config import Settings, AppEnvironment; app=create_app(Settings(_env_file=None, app_env=AppEnvironment.TEST, auth_mode='session')); print(app.title)"` passes;
  - `cd apps/web && npm run typecheck` passes;
  - `cd apps/web && npm run lint` passes with 4 pre-existing unused-symbol warnings;
  - `cd apps/web && npm run build` passes;
  - browser verification against `http://localhost:3000/login` and `/register` passes: pages render content,
    show no Next.js error overlay, and expose expected form controls;
  - `git diff --check` passes.

## Web Favicon

- Added a custom SVG favicon for the Next.js dashboard at `apps/web/app/icon.svg`.
- Updated `apps/web/app/layout.tsx` metadata to point `icons.icon` at `/icon.svg`.
- Verification:
  - `cd apps/web && npm run typecheck` passes;
  - `cd apps/web && npm run lint` passes with 4 pre-existing unused-symbol warnings;
  - `cd apps/web && npm run build` passes and emits `/icon.svg`;
  - `git diff --check` passes.

## Vercel API CORS Env Parsing Fix

- Fixed production startup failure on Vercel where `CORS_ALLOWED_ORIGINS` set as a comma-separated
  string caused Pydantic Settings to JSON-decode `list[str]` before the existing validator could split it.
- Updated `apps/api/app/config.py` to mark `cors_allowed_origins` with `NoDecode` so deploy dashboard values like
  `https://frontend.vercel.app,https://preview.vercel.app` load correctly.
- Added regression coverage in `apps/api/app/tests/test_config.py` for `CORS_ALLOWED_ORIGINS` from the actual
  environment variable path.
- Verification:
  - `cd apps/api && .venv/bin/pytest app/tests/test_config.py -q` passes;
  - `cd apps/api && .venv/bin/ruff check app/config.py app/tests/test_config.py` passes;
  - `cd apps/api && .venv/bin/ruff format --check app/config.py app/tests/test_config.py` passes;
  - `git diff --check` passes.

## Deployment Guidance

- Reviewed deployment shape for this repo:
  - `apps/web` is a standalone Next.js 15 dashboard with an existing production Dockerfile.
  - `apps/api` is the canonical FastAPI backend with an existing production Dockerfile and Alembic migrations.
  - Production runtime also needs managed Postgres; Redis is optional but needed for Redis-backed job queue paths/workers.
  - Recommended split is Vercel for `apps/web` and Render for `apps/api`, Postgres, Redis, and workers, or Render-only using Docker services.
- No code changes, deploy commands, tests, or builds were run.

## GitHub Issue #12 Daily Dashboard E2E Smoke

- Addressed GitHub issue #12 (`Add end-to-end smoke coverage for the daily dashboard workflow`).
- Added `apps/web/tests/e2e/daily-dashboard-workflow.spec.ts` covering:
  - populated demo workflow rendering across command center, brief, data onboarding, scanner, triage, setup detail,
    journal, outcome review, notifications, and quality routes;
  - non-crashing states when optional dashboard backend modules are unavailable;
  - visible safe-copy checks on the covered routes.
- Added `daily-workflow-populated` to the E2E mock API scenario list and extended
  `apps/web/tests/e2e/helpers/mockApiServer.mjs` with populated signal, setup context, report, quality, reasoning,
  candle, and outcome artifacts for setup-detail and daily dashboard routes.
- Updated `.github/workflows/web-ci.yml` to install Chromium and run `npm run test:e2e` after lint, typecheck, and build.
- Updated `apps/web/docs/e2e-smoke.md` to document CI execution and the expanded workflow coverage.
- Verification:
  - `cd apps/web && npm run typecheck` passes;
  - `cd apps/web && npm run lint` passes with 4 pre-existing unused-symbol warnings;
  - Playwright tests were not run per user instruction.

## GitHub Issue #11 API Docker Reproducibility

- Addressed GitHub issue #11 (`Make the API Docker image production-oriented and reproducible`).
- Added `apps/api/constraints-runtime.txt` with pinned runtime dependency versions for the production API image.
- Updated `apps/api/Dockerfile` so the production image installs `.` with `--constraint constraints-runtime.txt` and does
  not install the `dev` extra.
- Left `apps/api/Dockerfile.dev` as the dev/test image path with `.[dev]`, keeping pytest, Ruff, mypy, and HTTP test
  tooling available outside the runtime image.
- Updated `apps/api/README.md` with the production Docker build command, a `docker run` example, and expected runtime
  environment variables including `DATABASE_URL`, `AUTH_ENABLED`, `AUTH_MODE`, `ADMIN_API_KEY`, and
  `API_KEY_HEADER_NAME`.
- Verification:
  - constraints check confirms all 14 direct runtime dependencies are covered and dev tooling is excluded;
  - `cd apps/api && .venv/bin/python -m pip install --dry-run --constraint constraints-runtime.txt .` passes;
  - `rg -n "\\[dev\\]|constraints-runtime|pip install" apps/api/Dockerfile apps/api/Dockerfile.dev apps/api/README.md`
    confirms `.[dev]` remains only in local/dev docs and `Dockerfile.dev`;
  - `git diff --check` passes;
  - `docker build -f apps/api/Dockerfile -t trading-intelligence-api:issue-11 .` could not run because the local
    Docker daemon socket was unavailable.

## GitHub Issue #10 Backend RBAC Route Coverage

- Addressed GitHub issue #10 (`Audit RBAC dependency coverage across mutating backend routes`).
- Added route-level `Depends(require_permission(...))` coverage to mutating backend route decorators that were missing
  explicit RBAC guards across analysis, market data, runtime/admin, notification, journal, scanner, strategy profile,
  and related intelligence modules.
- Left seven intentional write-free validation/preview POST routes unguarded at route level and documented them as
  explicit exemptions:
  - `POST /chart-screenshot-runs/image/preview`;
  - `POST /data-contracts/validate`;
  - `POST /data-contracts/validate-source`;
  - `POST /safety-policies/evaluate-action`;
  - `POST /safety-policies/evaluate-payload`;
  - `POST /safety-policies/evaluate-text`;
  - `POST /state-machines/validate-transition`.
- Updated `apps/api/docs/rbac-route-coverage.md` with the mutating route permission map and exemption table.
- Added `apps/api/app/tests/unit/test_rbac_route_coverage.py`, which scans `app/modules/**/routes.py` and fails when a
  new mutating route lacks `require_permission`, `require_admin`, or an explicit exemption.
- Verification:
  - source inventory reports `total=246 missing=0 exempt=7`;
  - `cd apps/api && .venv/bin/pytest app/tests/unit/test_rbac_route_coverage.py -q` passes;
  - `cd apps/api && .venv/bin/ruff check app/tests/unit/test_rbac_route_coverage.py app/modules/*/routes.py` passes;
  - `cd apps/api && .venv/bin/ruff format --check app/tests/unit/test_rbac_route_coverage.py app/modules/*/routes.py`
    passes.

## GitHub Issue #9 Setup Detail Journal API Client

- Addressed GitHub issue #9 (`Route setup-detail journal submission through the shared API client`).
- Updated `apps/web/src/components/setup-detail/SetupJournalPanel.tsx` to submit journal entries via
  `createJournalEntry` from `apps/web/src/lib/api/journal.ts` instead of constructing a direct browser `fetch`.
- Removed the now-unused `apiBaseUrl` prop from the setup-detail and setup-review journal panel call chain.
- The setup-detail journal create path now inherits shared API timeout, auth header, error normalization, and
  browser mutation proxy behavior from `apps/web/src/lib/api/client.ts`.
- Verification:
  - `cd apps/web && npm run typecheck` passes;
  - `cd apps/web && npm run lint` passes with the 4 pre-existing unused-symbol warnings.

## GitHub Issue #8 Web Mutation Auth Proxy

- Addressed GitHub issue #8 (`Make frontend mutating API calls compatible with AUTH_ENABLED=true`).
- Added server-only Next.js mutation proxy at `apps/web/app/api/backend/[...path]/route.ts`.
- Browser-initiated `POST`, `PATCH`, `DELETE`, and form POST calls from the shared web API client now use the
  same-origin proxy instead of calling the backend origin directly.
- The proxy forwards to `WEB_API_PROXY_BASE_URL` and attaches `WEB_API_PROXY_ADMIN_API_KEY` using
  `WEB_API_PROXY_API_KEY_HEADER`, with fallback support for backend-style `ADMIN_API_KEY` and
  `API_KEY_HEADER_NAME`.
- Kept `NEXT_PUBLIC_*` env vars public-only; server API keys are documented as server runtime env only.
- Updated `apps/web/.env.example` and `apps/web/README.md` with the local/staging auth path and production caveat.
- Verification:
  - `cd apps/web && npm run lint` passes with the 4 pre-existing unused-symbol warnings;
  - `cd apps/web && npm run build` passes and includes `ƒ /api/backend/[...path]`;
  - `cd apps/web && npm run typecheck` passes after build-generated `.next/types` settle;
  - local runtime smoke with a mock backend requiring `x-api-key` returned HTTP 200 through
    `POST /api/backend/onboarding/actions` when `WEB_API_PROXY_ADMIN_API_KEY=proxy-secret`.

## GitHub Issue #7 Data Contract Schema Warning

- Addressed GitHub issue #7 (`Resolve DataContractRead schema_json Pydantic shadow warning`).
- Updated `apps/api/app/modules/data_contracts/schemas.py` so `DataContractRead` uses internal field
  `schema_definition` with `schema_json` validation and serialization aliases.
- Preserved the external API response contract: `model_dump(by_alias=True)` still emits `schema_json`.
- Added focused serialization coverage in `apps/api/app/tests/test_data_contract_validators.py`.
- Verification:
  - `cd apps/api && .venv/bin/pytest app/tests/test_data_contract_validators.py -q` passes with 4 tests;
  - `cd apps/api && .venv/bin/pytest --collect-only -q` collects 449 tests with no Pydantic shadow warning;
  - `cd apps/api && .venv/bin/ruff check app/modules/data_contracts/schemas.py app/tests/test_data_contract_validators.py` passes;
  - `cd apps/api && .venv/bin/pytest -q` passes with 399 passed and 50 skipped, with no Pydantic shadow warning.

## GitHub Issue #6 Pytest Top-Level Tests

- Addressed GitHub issue #6 (`Include top-level apps/api/tests files in default pytest collection`).
- Updated `apps/api/pyproject.toml` pytest `testpaths` from `["app/tests"]` to `["app/tests", "tests"]`.
- Confirmed API CI uses plain `pytest`, so the full default collection now includes the top-level tests.
- Verification:
  - before the change, `cd apps/api && .venv/bin/pytest --collect-only -q` collected 436 tests and omitted the top-level `tests/*.py` modules;
  - after the change, `cd apps/api && .venv/bin/pytest --collect-only -q` collected 448 tests and included `tests/test_profile_governance.py`, `tests/test_scenario_outcomes.py`, and `tests/test_timeframe_aggregation.py`;
  - `cd apps/api && .venv/bin/pytest tests/test_profile_governance.py tests/test_scenario_outcomes.py tests/test_timeframe_aggregation.py -q` passes with 12 tests.

## GitHub Issue Closure

- Posted completion comments and closed completed issues as `completed`:
  - #11 `Make the API Docker image production-oriented and reproducible`;
  - #10 `Audit RBAC dependency coverage across mutating backend routes`;
  - #9 `Route setup-detail journal submission through the shared API client`;
  - #8 `Make frontend mutating API calls compatible with AUTH_ENABLED=true`;
  - #7 `Resolve DataContractRead schema_json Pydantic shadow warning`;
  - #6 `Include top-level apps/api/tests files in default pytest collection`;
  - #3 `Fix backend Ruff failures so API CI can pass`;
  - #4 `Add reproducible frontend dependency lockfile and restore web typecheck`;
  - #5 `Add CI coverage for the Next.js web app`.

## GitHub Issue #5 Web CI

- Addressed GitHub issue #5 (`Add CI coverage for the Next.js web app`).
- Added `.github/workflows/web-ci.yml` for push and pull request changes under `apps/web/**` and the workflow file.
- CI uses Node 22 with npm cache keyed by `apps/web/package-lock.json`, then runs:
  - `npm ci`;
  - `npm run lint`;
  - `npm run typecheck`;
  - `npm run build`.
- Fixed the production build blocker by wrapping `WorkspaceSelector` in a Suspense boundary inside
  `apps/web/src/components/layout/WorkspaceSwitcher.tsx`, because `WorkspaceSelector` reads search params.
- Verification:
  - `cd apps/web && npm ci` passes;
  - `cd apps/web && npm run lint` passes with 4 pre-existing unused-symbol warnings outside this issue's touched files;
  - `cd apps/web && npm run typecheck` passes;
  - `cd apps/web && npm run build` passes.

## GitHub Issue #4 Web Lockfile and Typecheck

- Addressed GitHub issue #4 acceptance in `apps/web`.
- Confirmed `apps/web/package-lock.json` is committed and docs already point clean installs to npm/`npm ci`.
- Fixed web typecheck blockers found during verification:
  - corrected a mismatched JSX closing tag in `apps/web/src/components/setup-wizard/SetupWizardLayout.tsx`;
  - broadened shared motion helper element/return/child/style typing in `apps/web/src/components/ui/motion.tsx`;
  - made `cn` flatten nested class arrays in `apps/web/src/lib/ui/cn.ts`;
  - typed demo metric tuples in `apps/web/src/components/demo/DemoRunButton.tsx`.
- Verification:
  - `cd apps/web && npm ci` passes;
  - `cd apps/web && npm run typecheck` passes;
  - `cd apps/web && npm run lint` passes with 4 pre-existing unused-symbol warnings outside the touched files.

## GitHub Issue #3 Backend Ruff Cleanup

- Addressed GitHub issue #3 (`Fix backend Ruff failures so API CI can pass`) for `apps/api`.
- Ran Ruff safe fixes and formatting across `apps/api`, then fixed remaining lint categories manually:
  - FastAPI `Query`/`Depends` defaults now use `Annotated` where needed;
  - dynamic `Any` helper signatures were narrowed to concrete/object types;
  - long generated/model/query strings were wrapped without behavior changes.
- Verification:
  - `cd apps/api && .venv/bin/ruff check .` passes;
  - `cd apps/api && .venv/bin/ruff format --check .` passes;
  - `cd apps/api && .venv/bin/pytest --collect-only -q` collects 436 tests and still emits the pre-existing `DataContractRead.schema_json` Pydantic warning.
- Secondary check:
  - `cd apps/api && .venv/bin/mypy app` was run after Ruff; it still fails with 306 existing type errors across 67 files, so typecheck remains a separate follow-up after the Ruff unblock.

## Go Market Worker Live Startup Validation Retryability

- Updated `apps/go/market-worker/internal/live/service.go` so startup symbol/source lookup errors are retryable unless
  the row is truly missing (`pgx.ErrNoRows`).
- Missing/inactive symbol/source rows and non-live source types remain terminal hard-fail paths that mark subscriptions as
  `failed` and return success for that subscription run.
- Documented terminal-vs-retry classification in:
  - `apps/go/market-worker/README.md`
  - `apps/go/market-worker/OPERATIONS.md`
- Added retryable startup lookup observability:
  - `liveSubscriptionStartupLoadFailures` metric in `apps/go/market-worker/internal/health/metrics.go`;
  - `live_subscription_symbol_source_load_retryable` log/metric path in `apps/go/market-worker/internal/live/service.go`;
  - docs updates in `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md`.
- Scope remains code and documentation only; no tests/builds executed.

## Go Market Worker Live Subscription Failure Determinism

- Added deterministic terminal failure handling in `apps/go/market-worker/internal/live/service.go` so live
  subscriptions are marked `failed` even when optional `live_feed_events` persistence is unavailable.
- Applied `failSubscription` helper in terminal paths:
  - provider symbol resolution failure in `Process()`;
  - timeframe validation failure in `Process()`;
  - provider error messages in stream processing;
  - message parse-threshold exhaustion in stream processing.
- Updated
  `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md` to document that these status
  transitions are deterministic without `live_feed_events`.
- Added terminal-stream hard-stop for live provider error events in `apps/go/market-worker/internal/live/service.go` so
  terminal provider stream errors stop reconnect retries and directly classify the run as failed after failure
  marking.
- Extended startup hard-stop behavior in `apps/go/market-worker/internal/live/service.go`:
  - missing/invalid symbol/source state (`missing`, `inactive`, or non-`websocket_live`) now marks the subscription
    as `failed` and returns terminally for that run without propagating an error that would fan out as a process-level
    failure.
- Scope remains documentation and production code only; no tests/builds executed.

## Go Market Worker Live Stream Parse-Failure Circuit Breaker

- Added bounded consecutive parse-failure hard-stop for live stream parsing in
  `apps/go/market-worker/internal/live/service.go`.
- `MARKET_WORKER_LIVE_STREAM_MAX_MESSAGE_PARSE_FAILURES` was added to `apps/go/market-worker/internal/config/config.go`
  and exposed in startup/inspect output in `apps/go/market-worker/cmd/market-worker/main.go`.
- Added new metric `liveMessageParseThresholdExceeded` in `apps/go/market-worker/internal/health/metrics.go` to
  distinguish schema/stream corruption events from isolated parse retries.
- `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md` were updated with config,
  metric, and log guidance for parse-threshold tuning.
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Stream Parse Threshold Run Taxonomy

- Added `LiveSubscriptionRunsParseThresholdExceeded` in
  `apps/go/market-worker/internal/health/metrics.go` and wired it to increment when
  `errLiveSubscriptionMessageParseThresholdExceeded` terminates a live run.
- Updated docs to surface `liveSubscriptionRunsParseThresholdExceeded` in `/metrics.json` checks so operators can
  triage malformed-message storms separately from transient parse noise and reconnect churn.
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Stream Runtime

- Production-grade live stream runtime processing was reconnected in `apps/go/market-worker/internal/live` with
  subscription candidate claiming, lease renewal/release, websocket consumption, and stop-aware stream
  shutdown behavior in `apps/go/market-worker/internal/worker/runner.go`.
- `cmd/market-worker/main.go` now wires live service creation into `worker.NewRunner` and exposes live
  stream settings in inspect mode for operational verification.
- Added `MARKET_WORKER_LIVE_STREAM_MESSAGE_STALE_SECONDS` handling in live runtime candidate selection to skip
  stale websocket subscriptions without fresh `last_message_at` heartbeats during claim cycles.
- Added explicit stale subscription marking for operational visibility:
  each live claim cycle marks expired unleased subscriptions as `stale` and increments `liveSubscriptionsStale`.
- `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md` were updated with live
  run-time settings, tuning guidance, and metrics/log checks.
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Lease Lifecycle Hardening

- Added lease ownership loss handling in `apps/go/market-worker/internal/worker/runner.go` so a lost
  websocket lease now cancels stream processing immediately and stops writing while ownership is no longer
  held.
- Added lease lifecycle counters in `apps/go/market-worker/internal/health/metrics.go`:
  - `liveLeaseRenewals`
  - `liveLeaseRenewalFailures`
  - `liveLeaseLost`
  - `liveLeaseAcquisitionMisses`
  - `liveLeaseReleaseFailures`
- Added lease-loss and failed-release observability in `apps/go/market-worker/OPERATIONS.md` and
  `apps/go/market-worker/README.md`.
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Status Transition Hardening

- Added runtime status refresh checks during live message consumption in
  `apps/go/market-worker/internal/live/service.go` so paused/failed/stopped subscriptions stop promptly
  after DB status transitions.
- Added `liveSubscriptionsStopped` and log `live_subscription_status_stopped` to capture live stream
  lifecycle stop events.
- Updated `apps/go/market-worker/OPERATIONS.md` and `apps/go/market-worker/README.md` with stop-event
  observability guidance.
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Subscription Run Lifecycle Telemetry

- Added production-grade live stream run-lifecycle counters in `apps/go/market-worker/internal/health/metrics.go`:
  - `liveSubscriptionRunsCompleted`
  - `liveSubscriptionRunsFailed`
- Wired run termination classification in `apps/go/market-worker/internal/live/service.go` so the worker distinguishes:
  - completed runs from normal status stop, graceful context-driven shutdown, and reconnect-budget terminal exits;
  - failed runs from terminal stream initialization/reconnect failures and unexpected terminal stream errors.
- Updated runbook guidance so `/metrics.json` includes run completion/failure counters:
  - `apps/go/market-worker/OPERATIONS.md`
  - `apps/go/market-worker/README.md`
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Stream Reconnect Budget

- Added bounded reconnect attempt protection for live subscriptions in
  `apps/go/market-worker/internal/live/service.go` with new config `MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_ATTEMPTS`.
- Added explicit subscription failover metrics and logs when the reconnect budget is exceeded.
- Updated inspect output to include `liveStreamMaxReconnectAttempts` and documented failure triage in
  `apps/go/market-worker/OPERATIONS.md`.
- Continued production scope with code/docs only and no test/build execution.

## Go Market Worker Live Stream Read Stability Telemetry

- Added production-grade live stream parse-failure and read-timeout visibility in
  `apps/go/market-worker/internal/health/metrics.go` and
  `apps/go/market-worker/internal/live/service.go`.
- Added `liveReconnectReadTimeouts` and `liveMessageParseFailures` counters in
  `/metrics.json` to distinguish websocket read stall behavior from generic reconnect churn.
- Added dedicated stream-read-timeout logging with `live_subscription_stream_read_timeout`.
- Updated `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md`
  with the new failure-mode telemetry and triage checks.
- Scope remains code and documentation only. No tests/builds executed.

## Go Market Worker Live Stream Recovery Telemetry

- Added explicit stale-state recovery telemetry in `apps/go/market-worker/internal/live/repository.go`
  and `apps/go/market-worker/internal/live/service.go`.
- `RecordHeartbeat` now reports whether an active stream recovered from `stale` and emits
  `live_subscription_stale_recovered` with an operational counter and docs updates.
- Added `liveSubscriptionsRevived` in `/metrics.json` to surface how many subscriptions recovered
  from stale heartbeat misses.
- Updated `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md`
  to document revival behavior and triage checks.
- Scope remains code and documentation only. No tests/builds executed.

## Modern Motion UI Rollout – Command Center Row Deepening (Continuation)

- Added the remaining production-grade command-center row-level motion polish without logic or safety changes:
  - `apps/web/src/components/command-center/CommandCenterConfirmationPanel.tsx`
  - `apps/web/src/components/command-center/CommandCenterScanStatus.tsx`
  - `apps/web/src/components/command-center/CommandCenterNextActions.tsx`
  - `apps/web/src/components/command-center/CommandCenterJournalPrompt.tsx`
  - `apps/web/src/components/command-center/CommandCenterFreshnessPanel.tsx`
  - `apps/web/src/components/command-center/CommandCenterDailyScanButton.tsx`
  - `apps/web/src/components/command-center/CommandCenterErrorState.tsx`
- Updated rollout notes in:
  - `apps/web/docs/motion-ui.md`
- Scope remains documentation+code only; no tests/builds executed per request.

## Modern Motion UI Rollout – Command Center Deepening

- Production motion pass added to command-center high-value surfaces without contract or behavior changes:
  - `apps/web/src/components/command-center/CommandCenterHeader.tsx`
  - `apps/web/src/components/command-center/CommandCenterMorningBrief.tsx`
  - `apps/web/src/components/command-center/CommandCenterReadinessStrip.tsx`
  - `apps/web/src/components/command-center/CommandCenterNavigationGrid.tsx`
  - `apps/web/src/components/command-center/CommandCenterQuickActions.tsx`
  - `apps/web/src/components/command-center/CommandCenterPrioritySetups.tsx`
  - `apps/web/src/components/command-center/CommandCenterAvoidPanel.tsx`
  - `apps/web/src/components/command-center/CommandCenterOutcomeReview.tsx`
  - `apps/web/src/components/command-center/CommandCenterWorkflowStatus.tsx`
- Updated `apps/web/docs/motion-ui.md` with this production step and kept this commit scoped to code + docs only (no tests/builds run), as requested.

## Modern Motion UI Rollout – Setup Detail Reveal Deepening

- Completed production-grade staging motion pass for setup detail surfaces with existing shared primitives and no API/behavior contract changes:
  - `apps/web/src/components/setup-detail/SetupActionPlanPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupAuditPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupBiasSummary.tsx`
  - `apps/web/src/components/setup-detail/SetupDataQualityPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupDetailHeader.tsx`
  - `apps/web/src/components/setup-detail/SetupErrorSection.tsx`
  - `apps/web/src/components/setup-detail/SetupEvidencePanel.tsx`
  - `apps/web/src/components/setup-detail/SetupHistoricalCasesPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupOutcomeHistoryPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupQualityPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupReasoningPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupWaitAvoidPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupZonesPanel.tsx`
- Updated `apps/web/docs/motion-ui.md` with the same step-level rollout note and no-backend-change rationale.
- Commit/push task focused on code and documentation only (no tests/builds executed per instruction).

## Modern Motion UI Rollout – Onboarding Reveal Depth

- Applied a production-step onboarding reveal expansion using shared motion primitives:
  - `apps/web/src/components/onboarding/OnboardingShell.tsx`
  - `apps/web/src/components/onboarding/OnboardingHeader.tsx`
  - `apps/web/src/components/onboarding/OnboardingErrorState.tsx`
  - `apps/web/src/components/onboarding/ReadinessScorePanel.tsx`
  - `apps/web/src/components/onboarding/OnboardingNextStepPanel.tsx`
  - `apps/web/src/components/onboarding/OnboardingStepList.tsx`
  - `apps/web/src/components/onboarding/OnboardingStepCard.tsx`
  - `apps/web/src/components/onboarding/DemoWorkspaceCard.tsx`
  - `apps/web/src/components/onboarding/OnboardingCompletionPanel.tsx`
- Reused only public motion helpers (`AnimatedListItem`, `motionCardClass`, `motionRevealDensityStyle`, `motionRevealPresetClass`) and `cn` for class composition.
- No API/data contracts changed, no setup logic changes, and no build/test command execution.

## Modern Motion UI Rollout – Setup Wizard Reveal Depth

- Added compact/comfortable, row-level reveal motion to setup wizard surface components:
  - `apps/web/src/components/setup-wizard/SetupProgress.tsx`
  - `apps/web/src/components/setup-wizard/SetupSummary.tsx`
  - `apps/web/src/components/setup-wizard/WorkspaceStep.tsx`
  - `apps/web/src/components/setup-wizard/UserStep.tsx`
  - `apps/web/src/components/setup-wizard/SymbolsStep.tsx`
  - `apps/web/src/components/setup-wizard/DataSourceStep.tsx`
  - `apps/web/src/components/setup-wizard/CredentialStep.tsx`
  - `apps/web/src/components/setup-wizard/WatchlistStep.tsx`
  - `apps/web/src/components/setup-wizard/ScannerPresetStep.tsx`
  - `apps/web/src/components/setup-wizard/PreferenceProfileStep.tsx`
  - `apps/web/src/components/setup-wizard/DemoDataStep.tsx`
  - `apps/web/src/components/setup-wizard/ReadinessStep.tsx`
  - `apps/web/src/components/setup-wizard/FirstScanStep.tsx`
- Kept shared public motion API usage only: `AnimatedListItem`, `motionCardClass`, `motionRevealDensityStyle`, `motionRevealPresetClass`, and `cn`.
- Kept behavior and contracts unchanged: no backend or safety copy edits, no route-level data-flow changes.
- Documentation update included:
  - `apps/web/docs/motion-ui.md` (production step note added).
- Verification commands were intentionally skipped per request; commit/push only.

## Modern Motion UI Rollout – Setup/equity/preferences/demo depth

- Added staged reveal motion to setup and high-density research/preference/demo surfaces:
  - `apps/web/src/components/setup-wizard/SetupWizardLayout.tsx`
  - `apps/web/src/components/equity-research/EquityResearchHeader.tsx`
  - `apps/web/src/components/equity-research/EquityUniversePanel.tsx`
  - `apps/web/src/components/equity-research/EquityUniverseMembers.tsx`
  - `apps/web/src/components/equity-research/SwingCandidateTable.tsx`
  - `apps/web/src/components/equity-research/SwingCandidateDetail.tsx`
  - `apps/web/src/components/preferences/PreferenceProfileSummary.tsx`
  - `apps/web/src/components/preferences/PreferenceProfileList.tsx`
  - `apps/web/src/components/demo/DemoModeHeader.tsx`
  - `apps/web/src/components/demo/DemoFlowSteps.tsx`
  - `apps/web/src/components/demo/DemoResultLinks.tsx`
  - `apps/web/src/components/demo/DemoRunButton.tsx`
  - `apps/web/src/components/demo/DemoDisabledState.tsx`
- Route-level page entry already maintained at `apps/web/app/demo/page.tsx` with list-item sequencing.
- Reused shared API only from `@/lib/ui/motion`:
  - `AnimatedListItem`
  - `motionCardClass`
  - `motionRevealDensityStyle`
  - `motionRevealPresetClass("scale-subtle")`
- Updated documentation-only in this pass:
  - `apps/web/docs/motion-ui.md`
- No backend/API contracts changed. Scope remains code/documentation only, no tests or build runs.

## Modern Motion UI Rollout – Dashboard & Notifications Reveal Hardening

- Extended motion sequencing to remaining high-density dashboard and notification row surfaces while keeping all data flow/read/write contracts unchanged:
  - `apps/web/src/components/dashboard/market-board.tsx`
  - `apps/web/src/components/dashboard/watchlist-panel.tsx`
  - `apps/web/src/components/dashboard/follow-up-panel.tsx`
  - `apps/web/src/components/dashboard/backend-state-panel.tsx`
  - `apps/web/src/components/dashboard/signal-focus-panel.tsx`
  - `apps/web/src/components/dashboard/signal-digest-panel.tsx`
  - `apps/web/src/components/notifications/NotificationList.tsx`
  - `apps/web/src/components/notifications/NotificationCard.tsx`
- Motion primitives used:
  - `AnimatedListItem`
  - `motionCardClass`
  - `motionRevealDensityStyle(index, "compact")`
  - `preset="scale-subtle"`
- No backend/API contract changes were introduced.
- Scope remains code and documentation focused (no tests/builds executed).

## Modern Motion UI Rollout – Quality Route Reveal Deepening

- Applied compact staggered row/card motion to remaining major `/quality` sections with high visual density:
  - `apps/web/src/components/quality/CohortDriftPanel.tsx`
  - `apps/web/src/components/quality/ConfidenceCalibrationPanel.tsx`
  - `apps/web/src/components/quality/PatternAttributionPanel.tsx`
  - `apps/web/src/components/quality/ProfileReliabilityTable.tsx`
  - `apps/web/src/components/quality/QualityWarningsPanel.tsx`
  - `apps/web/src/components/quality/SymbolTimeframeQualityGrid.tsx`
  - `apps/web/src/components/quality/WalkForwardPanel.tsx`
- Motion primitives added with existing shared API only:
  - `AnimatedListItem`
  - `motionCardClass`
  - `motionRevealDensityStyle(index, "compact")`
  - `motionRevealPresetClass("scale-subtle")` or default preset where table-row animation should remain minimal.
- Kept behavior and data contracts unchanged; no backend/API modifications; no tests/builds executed per instruction.

## Modern Motion UI Rollout – Row Reveal Completion

- Added staggered row-level reveal motion to remaining high-value list surfaces without API or behavior changes:
  - `apps/web/src/components/outcomes/outcome-list.tsx`
  - `apps/web/src/components/signals/confidence-list.tsx`
  - `apps/web/src/components/signals/risk-note-list.tsx`
  - `apps/web/src/components/scanner/ScanResultSignalList.tsx`
  - `apps/web/src/components/journal/JournalEntryList.tsx`
- Kept existing styling and semantics intact while adding:
  - `AnimatedListItem`
  - `motionCardClass`
  - `motionRevealDensityStyle(..., "compact")`
  - `motionRevealPresetClass("scale-subtle")`
- Constraints followed this task: code and documentation only (no tests/builds), strict TS preserved, no backend/API contract changes.
- Next verification step (if permitted later): run `cd apps/web && npm run lint` and `cd apps/web && npm run typecheck`.

## Motion UI Rollout – Component-Level Reveal Depth

- `SymbolDetailView` now uses staged `AnimatedListItem` reveals for header, memory snapshot cards, signal rows, and analysis-run/scan detail rows through the existing shared motion API.
- `OnboardingWorkflow` now applies motion sequencing for hero/header, provider-health panel, step navigation buttons, active step panel, and previous/next controls.
- Updated `apps/web/docs/motion-ui.md` with the component-level production reveal-depth notes.
- No API contracts or safety-language changed; focus remained on animation and documentation updates only.

## Motion UI Rollout Audit Report Artifact Step

- Added markdown report generation support to `apps/web/scripts/motion-rollout-audit.mjs`:
  - `--report` flag in strict/JSON and non-JSON modes
  - `--report-path=<path>` with default `apps/web/docs/motion-rollout-audit-report.md`
  - markdown payload now includes manifest/version summary, route checks table, and manifest validation section
- Added `motion:rollout-audit:report` script in `apps/web/package.json` (strict JSON + report mode).
- Updated `apps/web/docs/motion-ui.md` with report command usage and flag notes.
- Added durable memory note in `docs/project-state.md` that the audit now emits a tracked markdown report artifact.
- Generated report file at `apps/web/docs/motion-rollout-audit-report.md`.
- Added non-JSON `--report` flow and documented `motion:rollout-audit` governance commands in `apps/web/README.md`.

## Motion UI Rollout Audit Completion (Strict Coverage)

- Completed manifest-driven motion rollout strictness:
  - Fixed route normalization to treat `app/page.tsx` as root (`""`) so `exemptRoutes: [""]` works.
  - Added `motionRevealDensityStyle(0)` to `apps/web/app/journal/[entryId]/page.tsx` to satisfy strict helper-token requirements.
  - Kept all behavior and contracts unchanged; no tests or builds were run.

## Motion UI Rollout – Manifest-Driven Audit Hardening

- Added manifest-driven rollout governance for motion entry checks:
  - `apps/web/scripts/motion-rollout-manifest.json`
  - `apps/web/scripts/motion-rollout-audit.mjs`
- Extended audit script behavior to enforce public motion API usage (`@/lib/ui/motion`) and provide strict/JSON modes:
  - `npm run motion:rollout-audit`
  - `npm run motion:rollout-audit:json`
  - `--allow-legacy` as an explicit temporary override flag
- Updated `apps/web/docs/motion-ui.md` and `docs/project-state.md` with this production-grade governance step.
- Commit requested and pushed: `6a92abe` on `main`.

## Motion UI Rollout – Manifest Schema Strictness (Strict Mode)

- Upgraded `motion:rollout-audit` for production-grade strict mode:
  - manifest schema checks now validate `route`, `page`, `requires`, and optional `revealDensity`
  - `motion:rollout-audit:strict` now maps to explicit `--strict`
  - manifest validation failures are captured and surfaced in JSON `manifestValidationIssues`
- Added `revealDensity` metadata to every route entry in `motion-rollout-manifest.json` to retain cadence intent for future rollouts.
- Commit created and pushed for this step in `main`.

## Motion UI Rollout – Production Route Audit Automation

- Added `apps/web/scripts/motion-rollout-audit.mjs` and wired `motion:rollout-audit` in
  `apps/web/package.json` to enforce route-level motion rollout presence during development and
  pre-merge checks.
- Updated `apps/web/docs/motion-ui.md` and `docs/project-state.md` with the rollout governance
  automation step and usage guidance.
- Kept scope strictly code/documentation-focused with no tests/builds run in this task.
- Committed as `48e9641` and pushed to `main`.

## Restrictive License Task

- Added root `LICENSE` with a proprietary all-rights-reserved license.
- Updated root `README.md` license section to point at `LICENSE` and describe the restrictive
  permission boundary.
- Updated `docs/project-state.md` with the durable restrictive licensing constraint.

## Root README Product/Technical Refresh

- Updated root `README.md` to reflect latest product state with badges, product-focused upper half,
  and technical architecture/runbook second half.
- Added current surfaces for onboarding, setup, readiness, demo, equity research, equity data
  background operations, Go market worker, job queue, and observability.
- Preserved safety boundary: read-only market intelligence only; no broker execution,
  auto-trading, copy trading, external trading alerts by default, raw-secret storage, or financial
  advice.
- Verification: `git diff --check -- README.md` passed.

## Equity Swing Research Mode

- Added backend module `apps/api/app/modules/equity_research/` with universes, members, deterministic swing scans, candidate scoring, and manual catalyst context.
- Added Alembic revision `202605071000_add_equity_research.py`.
- Added web route `/equity-research`, API client/types/labels, and equity research components for universes, members, scan form, candidate ranking/detail, and catalyst context.
- Added docs: `apps/api/docs/equity-research.md` and `apps/web/docs/equity-research.md`.
- Safety boundary: research/review only; no broker execution, auto-trading, copy trading, direct action instructions, signal-classification overrides, or financial advice.

## Equity Data Provider Foundation

- Added backend module `apps/api/app/modules/equity_data/` and migration
  `202605071100_add_equity_data_foundation.py`.
- Added deterministic mock provider, CSV/JSON row import, provider skeletons, symbol creation,
  universe attachment, metadata snapshots, fundamentals snapshots, earnings events, provider
  request history/errors, provider capability APIs, and earnings-to-catalyst conversion.
- Updated equity swing scoring to read latest metadata, fundamentals, and earnings context when
  available.
- Added `/equity-research` panels for provider status, universe import, data readiness, metadata,
  fundamentals, earnings, catalyst enrichment, and provider request history.
- Provider credential references are used by id only; no raw provider secrets are accepted or
  stored. External provider adapters are safe stubs unless explicitly enabled and configured.
- Commit requested: `Add equity data provider foundation`; stage only files changed for this task.

## Equity Data Background Operations V1

- Added `equity_data_operations` via Alembic revision
  `202605071200_add_equity_data_operations.py`.
- Added backend operation service, CSV file parser, credential readiness resolver, and
  `equity_data.operation` job queue handler on queue `equity_data`.
- Added `/equity-data/operations` list/detail plus universe import, file import, metadata,
  fundamentals, earnings, and earnings-to-catalysts operation endpoints.
- Added `/equity-research` panels for CSV file import, background operation history, and queued
  enrichment controls.
- Safety: raw uploaded CSV bytes are not persisted; sanitized queued rows are bounded by
  `EQUITY_DATA_MAX_QUEUED_IMPORT_ROWS`; raw credential/provider secret values are redacted and not
  exposed. Real Polygon/Alpaca network fetches and secret-manager value retrieval remain deferred.
- Verification so far: backend compile passed; targeted Ruff on changed backend files passed;
  `pytest app/tests/unit/test_equity_data.py` passed with one pre-existing
  `schema_json` warning from data-contract schemas. Full `ruff check app alembic` still reports many
  pre-existing lint findings outside this task.

## Go Market Data Worker Foundation Task

- Added first Go sidecar under `apps/go/market-worker`.
- Python remains canonical for FastAPI, auth/RBAC, SQLAlchemy/Alembic, orchestration,
  deterministic intelligence, LLM/reporting, and UI contracts.
- Go worker scope is market data ingestion only: job/provider polling bridge, mock/Binance public
  REST providers, candle normalization/validation, existing final/partial candle write semantics,
  optional provider health, ingestion performance/conflict diagnostics, runtime heartbeat, and
  local health/metrics endpoints.
- No Python migrations were added and existing Python provider polling/live ingestion paths were
  not removed or rerouted.
- Verification: `git diff --check` passed. `gofmt`, `go test ./...`, `go vet ./...`, and
  `go build ./cmd/market-worker` could not run because `go`/`gofmt` are not installed in this
  workspace.
- Follow-up hardening added `serve`, `once`, and `inspect` run modes, terminal versus retryable job
  failure handling, configurable retry backoff, and `apps/go/market-worker/OPERATIONS.md`.
- User requested no real tests or builds for the follow-up step; focus stayed on code and detailed
  documentation.
- Current follow-up adds production worker execution hardening: `MARKET_WORKER_MAX_CONCURRENCY`,
  context-aware bounded parallel processing, `job_queue_items.locked_until` renewal for long-running
  claimed jobs, lock renewal metrics, and docs updates. User again requested no real tests or builds.
- Current follow-up adds provider backpressure for the Go worker:
  `MARKET_WORKER_PROVIDER_MAX_CONCURRENCY`, `MARKET_WORKER_PROVIDER_MIN_INTERVAL_MS`, per-provider
  fetch gating, provider gate wait metrics, and documentation updates. User again requested no real
  tests or builds.
- Current follow-up adds per-provider circuit breaking:
  `MARKET_WORKER_PROVIDER_FAILURE_THRESHOLD`, `MARKET_WORKER_PROVIDER_COOLDOWN_SECONDS`,
  provider_circuit_open retryable failures, provider circuit metrics, and documentation updates.
  User again requested no real tests or builds.
- Current follow-up adds bounded job/request execution:
  `MARKET_WORKER_JOB_TIMEOUT_SECONDS`, `MARKET_WORKER_DB_WRITE_TIMEOUT_SECONDS`, job_timeout
  classification, timeout metrics, and documentation updates. User again requested no real tests or
  builds.
- Current follow-up adds stale direct request recovery:
  `MARKET_WORKER_PROVIDER_REQUEST_STALE_SECONDS`, Go-owned `provider_polling_requests` reclaiming,
  providerRequestsReclaimed metrics, and documentation updates. User again requested no real tests
  or builds.
- Current follow-up adds schema contract hardening:
  required table/column readiness checks, inspect and `/readyz` required/optional column problem
  reporting, optional integration column gating, and documentation updates. User again requested no
  real tests or builds.

## Motion UI Rollout Production Hardening

- Added motion density/profile exports in `apps/web/src/components/ui/motion.tsx` for
  `compact`/`regular`/`comfortable` reveal behavior and profile-based motion styles.
- Re-exported the new profile types/helpers in `apps/web/src/lib/ui/motion.ts`:
  `MotionRevealDensity`, `MotionRevealProfile`, `MOTION_REVEAL_PROFILES`, `motionRevealDensityStyle`,
  `motionRevealProfileStyle`, `DEFAULT_MOTION_REVEAL_STEP_MS`, `COMFORT_MOTION_REVEAL_STEP_MS`.
- Extended `apps/web/docs/motion-ui.md` with rollout manifest, route matrix, and production checklist.
- Updated `docs/project-state.md` with motion rollout governance as a durable memory item.
- Finalized the second hardening pass by applying `MOTION_INTERACTIVE_CLASS` to remaining shared
  primitives (`MetricCard`, `Section`, `PageHeader`) so hover/focus polish remains centralized.
- Migrated component callsites away from `motionRevealClass()` in command-center, brief, triage, and
  shell nav components to new preset-based `motionRevealPresetClass()` while keeping legacy exports
  in place for compatibility.
- Added production API deprecation notes and migration gate for the legacy motion helper path (`motionRevealClass`
  and `motionRevealStyle`) so new work uses `motionRevealPresetClass`, `motionRevealDensityStyle`,
  and `motionRevealProfileStyle`.
- Added runtime migration telemetry in the motion primitive for dev-time one-time warnings when compatibility helpers are used, to surface legacy calls during route testing and PR review.

## Go Additive Architecture Discussion

- User wants to preserve existing Python/FastAPI work and add Go only for future features where it
  is a better fit.
- Recommended boundary: keep Python as the canonical API, orchestration, deterministic
  intelligence, persistence, and UI-facing contract layer; add Go as optional sidecar workers for
  high-throughput live ingestion, streaming fan-out, background cleanup, provider connectors, and
  load/performance tooling.
- Do not migrate existing Python modules just to introduce Go.

## First-Run Onboarding Readiness Flow

- Current task: add first-run onboarding, readiness gate, workspace selector, safe setup actions,
  command-center readiness banner, docs, tests, commit, and push.
- Backend additions: `/onboarding/status`, `/onboarding/actions`, and
  `/workspaces/default-context`, composed from existing readiness/setup/demo/workspace services
  without new tables.
- Web additions: `/onboarding`, onboarding components/client/types, workspace selector local
  storage helper, and command-center readiness banner.
- Preserve unrelated `docs/project-state.md` deletion when staging; hunk-stage only this task's
  project-state addition.

## Daily Workflow E2E Smoke Harness Task

- Added Playwright foundation under `apps/web` with `test:e2e`, `test:e2e:headed`, and
  `test:e2e:ui` scripts.
- Added `apps/web/playwright.config.ts` to start a mock API server plus Next dev server with
  `NEXT_PUBLIC_API_BASE_URL` pointed at the mock API.
- Added E2E fixtures/helpers/specs under `apps/web/tests/e2e` for onboarding, command center,
  navigation, quick actions, optional endpoint fallbacks, and visible safe-copy checks.
- Added `apps/web/docs/e2e-smoke.md` plus README notes for the no-DB/no-provider mocked API
  approach.
- User explicitly stopped test execution mid-run; do not run more tests in this task.
- Verification completed before stop request: `cd apps/web && npm run typecheck` passed;
  `cd apps/web && npm run lint` passed with three pre-existing warnings in scanner/outcome/setup
  chart files.
- Preserve the pre-existing unrelated `docs/project-state.md` deletion hunk when staging; stage
  only the new E2E smoke harness project-state addition from that file.

## Production Hardening Foundation Integration

- Integrated the five production-hardening branches already present in the worktree by adding
  Alembic merge revision `202605061100_production_hardening_merge`.
- Extended product readiness to inspect provider credential reference status, read model
  availability, runtime supervisor persisted state, and existing live worker health without running
  hidden setup, scans, workers, provider calls, notifications, broker workflows, or advice flows.
- Updated API env/docs with production auth, read model, provider credential, runtime supervisor,
  and readiness settings.
- Verification: `alembic heads`, backend compile, Ruff on changed backend files, FastAPI route
  duplicate check, targeted auth/provider credential/runtime/read model tests, web typecheck,
  public web safety-language scan, and `git diff --check`.
- `alembic current` was not run successfully because `DATABASE_URL` is not configured in this
  worktree environment.

## Distributed Job Queue Platform Task

- Current task: add additive backend job queue abstraction under `apps/api/app/modules/job_queue/`.
- Planned/implemented scope: DB-backed durable job definitions/items/events, Redis adapter path,
  queue service, dispatcher, worker entrypoint, API routes, migration, docs, and focused tests.
- Safety boundary: no broker execution, order jobs, arbitrary code execution, shell execution,
  auto-trading, or financial-advice behavior.
- Commit requested: `Add distributed job queue platform`; stage only this branch/task files.

## Product State / Scalability Review

- Reviewed `docs/project-state.md`, local session memory, README/API docs, backend entrypoint,
  settings, security/operations docs, worker files, and route count for product-state assessment.
- Current backend is broad and artifact-driven: 88 backend module directories, 81 route modules, and
  481 loaded FastAPI method/path pairs.
- Key current gaps identified for future work: real identity provider/auth context, complete RBAC
  coverage audit, non-stub external notification adapters, stronger deployment packaging, full
  frontend CI/typecheck dependency state, larger-scale background queue/import execution, production
  observability/alerting, provider integration depth, and load/performance validation.
- No code changes were made for product behavior.

## Modern UI Integration Task

- Current task: reconcile the five completed web UI/productization branches into one cohesive
  Tailwind-native product UI.
- Integration focus: canonical app shell/navigation, shared UI/status primitives, typed fail-soft
  API clients, page compatibility, documentation, and safe non-advisory language.
- Code changes made in this task preserve workspace-aware navigation across desktop/mobile shell
  links, expose Dashboard and Review Outcomes in the primary mobile product map, simplify
  `WorkflowLinks`, modernize the legacy app navigation compatibility component, and pass setup
  detail workspace context into `AppShell`.
- Backend code was not changed in this integration pass.

## Current State

Repository is the AI Trading Intelligence Agent: deterministic market-intelligence backend plus a
read-only daily dashboard web surface. Product scope remains market intelligence only: no broker
execution, copy trading, auto-trading, external signal delivery, or financial-advice output.

## Current Task: Command Center and Brief Redesign

- Redesigning `/command-center` as the default premium daily cockpit with a hero/status band,
  review-first setup table, confirmation strip, avoid conditions, data reliability, outcome review,
  workflow progress, notifications/review items, and navigation.
- Redesigning `/brief` as a structured narrative summary with period/watchlist context, summary
  stats, what changed, fresh symbols, review-first setups, confirmation needs, avoid conditions,
  outcomes ready, watch-next context, backend-safe actions, and data-quality context.
- API composition remains fail-soft: backend daily brief is preferred; existing frontend fallback
  composition is preserved; provider polling and product readiness are optional command-center
  inputs.
- Safety boundary remains non-advisory market intelligence only. No broker execution, hidden
  provider calls, external notification delivery, auto-trading, or financial-advice output.
- Preserve unrelated staged/unstaged worktree changes outside this task. Use isolated staging for
  the final commit so unrelated data-onboarding, scanner, journal, quality, layout, and README
  changes are not included accidentally.
- Verification so far: `npm run typecheck` failed because `tsc` is not installed; `npm run lint`
  failed because `next` is not installed; targeted safe-language scan and `git diff --check` for
  changed command-center/brief files passed.

## Modern Motion UI Rollout Task

- Implemented the shared motion foundation layer with typed motion APIs and reveal/list-item helpers in `apps/web/src/components/ui/motion.tsx` plus export wiring in `apps/web/src/lib/ui/motion.ts`.
- Added CSS/animation utilities and reduced-motion overrides in `apps/web/app/globals.css` and configured motion entries in `apps/web/tailwind.config.ts`.
- Applied conservative motion/hover polish across shared UI primitives and layout primitives (`Card`, `Surface`, `Section`, `PageHeader`, `Button`, `MetricCard`, `Skeleton`, `Badge`, shell/nav primitives).
- Added section/page entry wrappers to all requested route entry points: `command-center`, `dashboard`, `triage`, `brief`, `scanner`, `quality`, `notifications`, `journal`, `review/outcomes`, `readiness`, `onboarding`, `setup`, `data/onboarding`, `equity-research`, `preferences/strategy`, `demo`, `signals/[signalId]`, `symbols/[symbolId]`, and `journal/[entryId]`.
- Added staged row/panel-level reveal sequencing in `apps/web/src/components/setup-review/SetupReviewView.tsx` for setup/detail pages.
- Kept existing behavior and backend contracts unchanged; no execution/advisory endpoints or data contracts were introduced.
- Production hardening follow-up:
  - Added exported motion constants and defaults (`MOTION_VARIANTS`, `MOTION_PRESETS`, `BASE_MOTION_DURATION_MS`, `DEFAULT_MOTION_PRESET`) for safer adoption.
  - Added input clamping to motion delay/duration calculations in shared wrappers.
  - Added production documentation set: `apps/web/docs/motion-ui.md`.
  - Updated `apps/web/docs/design-system.md` and `apps/web/README.md` with motion governance links and usage expectations.
  - Standardized production imports to use the public motion API (`@/lib/ui/motion`) for app pages and shared components.
- Next hardening pass completed:
  - Migrated remaining high-density command-center/triage/brief/layout call sites from `motionRevealStyle(..., 45)` to `motionRevealDensityStyle(...)`.
  - Applied compact density on dense repeated rows and preserved default section density elsewhere.
  - Added rollout checkpoint note in `apps/web/docs/motion-ui.md`.

## Modern Motion UI Rollout Production Polishing Task

- Completed second production hardening pass for motion primitives and loading polish:
  - Fixed `motionClass` to honor `preset="none"` by applying `motion-no-motion` instead of allowing the default reveal animation to run.
  - Migrated shared loading placeholders from ad-hoc `animate-pulse` blocks to `ShimmerSkeleton` across:
    - `apps/web/app/dashboard/loading.tsx`
    - `apps/web/src/components/brief/BriefSkeleton.tsx`
    - `apps/web/src/components/command-center/CommandCenterSkeleton.tsx`
    - `apps/web/src/components/onboarding/OnboardingSkeleton.tsx`
    - `apps/web/src/components/triage/TriageSkeleton.tsx`
    - `apps/web/src/components/charts/ChartSkeleton.tsx`
  - Updated `apps/web/docs/motion-ui.md` with a production rollout note for shimmer standardization and the `none` preset behavior.
- User request was documentation-first for this pass; no tests/builds were run.

## Modern Motion UI Rollout Production Hardening Step

- Completed interaction normalization pass for shared primitives by removing direct `motion-hover-lift` usage from `Card`, `Surface`, and `Badge` non-interactive paths.
- Kept motion/focus polish intact only for explicit interactive states through `MOTION_INTERACTIVE_CLASS`, matching the centralized token contract.
- No backend/API contract changes; no tests or builds run by request.

- Added centralized loading placeholder hardening by routing legacy `Skeleton` to `ShimmerSkeleton` and preserving decorative loading semantics with `aria-hidden` defaults in `ShimmerSkeleton`.

## Modern Motion UI Rollout Production Loading Hardening

- Consolidated loading primitive behavior so `Skeleton` now renders through `ShimmerSkeleton` and remains accessibility-safe by default (`aria-hidden` true).
- This unifies fallback placeholder semantics without changing route-level loading boundaries, motion tokens, API contracts, or non-advisory copy.
- No tests or builds were run by request.

## Tailwind Design System and App Shell Task

- Implemented/normalized the Tailwind-native cockpit design system across shared UI primitives,
  status badges, app shell layout, navigation helpers, safe-label helpers, and documentation.
- Added modern token coverage in `apps/web/app/globals.css` and `apps/web/tailwind.config.ts`
  for background, surfaces, borders, foreground/muted text, accent/status colors, focus rings,
  soft shadows, and premium controls.
- Added shared files under `apps/web/src/components/ui/`: `Surface`, `MetricCard`,
  `SectionHeader`, `LoadingState`, `Skeleton`, `StatGrid`, `ActionBar`, `Tooltip`, and `Divider`.
- Added responsive app shell files under `apps/web/src/components/layout/`: `AppShell`, `Sidebar`,
  `Topbar`, `MobileNav`, `WorkspaceSwitcher`, `PageContainer`, and `ApiStatusIndicator`.
- Added/updated `apps/web/src/lib/ui/cn.ts`, `safeLabels.ts`, `formatters.ts`, `navigation.ts`,
  and `statusStyles.ts`; added `OutcomeBadge` compatibility wrapper.
- Applied workspace context to the shell across app routes and kept product copy read-only and
  non-advisory.
- Verification: `cd apps/web && npm run typecheck` failed because `tsc` is not installed in this
  worktree; `cd apps/web && npm run lint` failed because `next` is not installed; `git diff --check`
  passed; safe-language scan across `apps/web` and task docs passed.

## Daily Review Surface Polish Task

- Current branch/worktree task: redesign `/journal`, `/review/outcomes`, `/quality`, and
  `/notifications` as polished daily review surfaces.
- Added shared frontend review-surface components under
  `apps/web/src/components/review-surfaces/`.
- Refactored journal page with daily metrics, filters, optional symbol/timeframe context from
  analysis runs, improved reflection form/list/detail/review panels, and safe copy.
- Added `apps/web/src/components/outcome-review/` for the outcome review route with filtered queue
  table, journal prompts, summary metrics, and diagnostics panels.
- Refactored quality header/summary into the shared review surface and added a what-to-review focus
  panel for warnings, sample-size notes, and drift diagnostics.
- Refactored notifications header, metrics, filters, and inbox list while preserving backend
  read/acknowledge/archive actions in the detail panel.
- Updated `apps/web/README.md` and `docs/project-state.md` with the journal review loop, outcome
  review surface, quality dashboard, notification inbox, and non-advisory safety boundary.

Current task added the Guided Workspace Setup Wizard and Demo Data Flow in a worktree that already
contained unrelated in-progress demo mode, daily routine, design-system, and visual setup chart
changes. Preserve unrelated worktree changes unless explicitly asked.

## Guided Workspace Setup Task

- Added backend module `apps/api/app/modules/workspace_setup/`.
- Added setup persistence migration `202605051100_add_workspace_setup_runs.py` for
  `workspace_setup_runs` and `workspace_setup_step_results`.
- Added setup APIs under `/workspace-setup` for start, get run, complete step, skip step, finish,
  and demo workspace creation.
- Added settings:
  `WORKSPACE_SETUP_VERSION`, `WORKSPACE_SETUP_DEMO_DATA_ENABLED`,
  `WORKSPACE_SETUP_DEFAULT_MARKET`, and `WORKSPACE_SETUP_DEFAULT_TIMEFRAMES`.
- Added web `/setup` route, setup wizard components, setup API client, types, and validation.
- Readiness remediation links now point missing setup prerequisites to `/setup`.
- Added docs: `apps/api/docs/workspace-setup.md` and `apps/web/docs/workspace-setup.md`.
- Durable memory in `docs/project-state.md` was updated with the setup boundary.

## Verification

- `cd apps/api && .venv/bin/python -m compileall app/modules/workspace_setup app/main.py app/db/models.py app/config.py`
- `cd apps/api && .venv/bin/python -c "from app.main import create_app; app = create_app(); print(len(app.routes))"`
- `cd apps/api && .venv/bin/ruff check app/modules/workspace_setup app/main.py app/db/models.py app/config.py app/tests/conftest.py alembic/versions/202605051100_add_workspace_setup_runs.py`
- `cd apps/api && .venv/bin/alembic heads`
- `cd apps/api && .venv/bin/pytest app/tests/unit/test_workspace_setup.py`
- `git diff --check`
- `cd apps/web && npm run typecheck` failed because `tsc` is not installed in this worktree.

## Commit Notes

- Commit requested: `Add guided workspace setup wizard`.
- Stage only setup task files and setup-specific hunks from shared files.

## Visual Setup Chart Panels Task

- Branch: `visual-setup-chart-panels`.
- Added SVG-only chart panels for `/signals/[signalId]` using reusable chart components under
  `apps/web/src/components/charts/` and chart utilities under `apps/web/src/lib/charts/`.
- Added `SetupVisualPanel` and setup chart API composition using existing analysis-run, final candle,
  candle quality, setup context, advanced feature, report, and outcome data. No backend endpoint was
  added.
- Added docs in `apps/web/docs/visual-setup-charts.md` and durable project-state notes.
- Commit created and pushed: `82ee4cc Add visual setup chart panels`.
- Verification: `GIT_INDEX_FILE=/tmp/visual-setup-current.index git diff --cached --check`;
  safe-language scans for the chart files and staged additions; `cd apps/web && npm run typecheck`
  failed because `tsc` is not installed.
- After commit, the worktree still has an unrelated unstaged `docs/project-state.md` deletion of the
  daily routine implementation note; preserve unless explicitly asked.

## GitHub Issue Audit Task

- Audited the repo for top actionable issues and opened GitHub issues in
  `waqasraza123/Trading-Data-Analysis-Agent`.
- Created issues:
  #3 backend Ruff failures, #4 frontend lockfile/typecheck, #5 web CI, #6 skipped top-level API
  tests, #7 `schema_json` Pydantic warning, #8 frontend auth for mutating API calls, #9 setup-detail
  journal direct fetch, #10 RBAC coverage audit, #11 API Docker reproducibility, #12 dashboard E2E
  smoke coverage.
- Verification/evidence commands run:
  `git diff --check`,
  `cd apps/api && .venv/bin/python -m compileall app`,
  `cd apps/api && .venv/bin/alembic heads`,
  `cd apps/api && .venv/bin/ruff check app` failed with 374 findings,
  `cd apps/api && .venv/bin/pytest app/tests/unit/test_workspace_setup.py app/tests/unit/test_daily_workflows.py app/tests/unit/test_read_models.py` passed,
  `cd apps/api && .venv/bin/pytest --collect-only -q` collected 396 tests under `app/tests`,
  `cd apps/web && npm run typecheck` failed because `tsc` is not installed.

## Production Observability Task

- Current task: implement backend-only production observability metrics, tracing hooks, SLOs, and
  SLO snapshots.
- Added module target: `apps/api/app/modules/observability/`.
- Safety boundary: internal operational monitoring only. No broker execution, trading behavior,
  user alerts, external observability provider requirement, or financial-advice output.
- Preserve pre-existing worktree changes: `docs/project-state.md`, auth/config changes, and
  untracked auth/job queue/candle ingestion performance modules unless explicitly staging the
  observability-specific hunks.

## Daily-Use Workflow Integration Reconciliation

- Confirmed the five daily-use branches are present in the current branch lineage:
  daily briefs, daily workflows, scanner presets, quality scoreboard, and notification inbox.
- Alembic has one current head: `202605051100_workspace_setup`; the daily workflow branches already
  converge through `202605032000_daily_product_workflow_merge`.
- Confirmed backend route registration has no duplicate path/method pairs for the loaded FastAPI app.
- Added `apps/web/docs/daily-use-workflow.md`, linked it from `apps/web/README.md`, and tightened
  product-facing safe-language wording in API/web docs plus UI sanitizer source literals.
- Commit created and pushed: `fea7e07 Integrate daily-use trading intelligence workflow`.
- Verification: `cd apps/api && .venv/bin/alembic heads`; FastAPI route duplicate check;
  `cd apps/api && .venv/bin/python -m compileall app/main.py app/config.py app/db/models.py app/modules/daily_briefs app/modules/daily_workflows app/modules/scanner_presets app/modules/notifications`;
  product-facing safety-language scan; `git diff --check`; staged diff safety scan.
- `cd apps/web && npm run typecheck` failed because `tsc` is not installed.
- Unrelated unstaged `docs/project-state.md` change remains intentionally uncommitted.

## Triage And Setup Review Redesign

- Redesigned `/triage` around visible buckets: Review First, Needs Confirmation, Conflicted,
  Avoid / No Directional, Stale / Data Issue, and Review Required.
- Added triage symbol search and sort state, kept preference-profile scoping, priority sorting,
  optional endpoint fallbacks, and card-level evidence/risk/outcome summaries.
- Added feature-local setup review components under `apps/web/src/components/setup-review/` and
  helpers under `apps/web/src/lib/setup-review/`.
- `/signals/[signalId]` now uses `getSetupReview` and `SetupReviewView` for sticky setup summary,
  visual context, evidence/confidence, wait/avoid, historical context, reasoning, journal, audit,
  quality-gate, multi-timeframe, and cross-asset sections.
- Updated `apps/web/README.md` and `docs/project-state.md` with the review-only boundary and safe
  terminology.
- Verification note: `cd apps/web && npm run typecheck` failed because `tsc` is not installed in
  this worktree.

## Scanner and Data Onboarding Redesign Task

- Redesigned `/scanner` with a guided Tailwind workflow: scanner hero metrics, preset gallery
  fallback cards, watchlist/config management, explicit run-now panel, daily workflow side panel,
  scan history/detail, and produced signal review.
- Redesigned `/data/onboarding` around a seven-step source readiness flow: source,
  credentials/config, symbols/timeframes, freshness, gap detection, recovery plan, and ready summary.
- Added feature-local components:
  `apps/web/src/components/scanner/ScannerHero.tsx`,
  `apps/web/src/components/scanner/RunScanNowPanel.tsx`,
  `apps/web/src/components/data-onboarding/DataOnboardingHero.tsx`, and
  `apps/web/src/components/data-onboarding/CredentialConfigStep.tsx`.
- Updated `apps/web/README.md` and `docs/project-state.md` with scanner/onboarding workflow notes,
  backend endpoint behavior, credential safety, no hidden external calls, no broker execution, and
  no financial advice.
- Verification: `cd apps/web && npm run typecheck` failed because this worktree has no
  `apps/web/node_modules/.bin/tsc`.
- Important staging note: the worktree still contains unrelated edits outside this task plus the
  pre-existing unstaged `docs/project-state.md` deletion. Stage only this task's files and the new
  project-state hunk.

## Production Docker CI Dev Setup Task

- Implemented production/dev Dockerfiles for API and web, root `.dockerignore`, root
  `docker-compose.yml`, dev compose override, `Makefile`, and reusable scripts under `scripts/`.
- Generated `apps/web/package-lock.json` using npm and added explicit frontend lint dependencies
  plus Next.js standalone output for reproducible web builds.
- Added `.github/workflows/ci.yml` with backend Ruff/mypy/pytest/Alembic checks, frontend
  lint/type/build checks, and Docker image builds.
- Updated root, API, web, development, deployment, and project-state docs with local setup,
  production image, worker, migration, seed, CI, env, lockfile, and integration-test guidance.
- Verification for this task should include shell syntax checks, npm lint/type/build where local
  deps permit, API Alembic heads/history, Docker build checks where available, and `git diff --check`.

## Production Auth Identity Isolation Task

- Added production auth module under `apps/api/app/modules/auth/` with dev, API-key, JWT, and mixed
  identity resolution, hashed API-key management, RS256 JWT verification, current identity/context
  routes, and workspace-aware permission helpers.
- Added auth persistence migration `202605061000_auth_identity_api_keys` for `auth_identities` and
  `auth_api_keys`.
- Updated existing permission dependency compatibility surface to delegate to auth dependencies
  while preserving local pass-through and legacy admin API-key behavior.
- Added focused protections for high-risk mutating routes: provider credentials, live writes,
  data-quality runs, candle gap recovery, analysis lifecycle, daily workflows/briefs/digests,
  setup context, market memory, read model rebuilds, runtime supervisor, readiness run, signal
  priority, and symbol admin writes.
- Added frontend public auth header support for dev user/workspace headers and optional browser
  storage bearer tokens.
- Added docs: `apps/api/docs/auth.md` and `apps/api/docs/rbac-route-coverage.md`; updated API/web
  READMEs, permissions docs, and durable project state.
- Verification: API targeted ruff passed; auth/config/operational targeted pytest passed; compileall
  passed; FastAPI app loads with 501 routes; `git diff --check` passed. `apps/web npm run
  typecheck` failed because `tsc` is not installed. `alembic heads` reports multiple heads because
  unrelated untracked/staged migrations are present in the worktree.

## High-Volume Candle Ingestion Performance Task

- Added backend module `apps/api/app/modules/candle_ingestion_performance/` with run/conflict
  persistence, chunk helpers, bulk candle write classification, progress tracking, diagnostics, and
  read APIs under `/candle-ingestion/performance-runs`.
- Added migration `202605061000_add_candle_ingestion_performance.py` for
  `candle_ingestion_performance_runs` and `candle_ingestion_conflicts`.
- Integrated existing CSV import, JSON import, and provider polling storage with chunked
  validation, batch existing-candle prefetch, batched inserts, consolidated updates, progress
  counters, and conflict records while preserving final/partial candle semantics.
- Added settings: `CANDLE_INGESTION_BATCH_SIZE`,
  `CANDLE_INGESTION_MAX_ROWS_PER_REQUEST`, `CANDLE_INGESTION_ENABLE_COPY_PATH`, and
  `CANDLE_INGESTION_PROGRESS_EVERY_ROWS`.
- Added docs: `apps/api/docs/candle-ingestion-performance.md`; updated API README and durable
  project state with the backend-only safety boundary.
- Verification: focused compile, focused Ruff, `pytest app/tests/unit/test_candle_ingestion_performance.py`,
  `git diff --check`, app route smoke check. `alembic heads` currently shows additional unrelated
  uncommitted heads for auth, job queue, and observability in this worktree.

## Daily Command Center Workflow Task

- Added `workspace_overview` and `workspace_actions` backend modules with
  `/workspaces/{workspace_id}/overview` and `/workspaces/{workspace_id}/quick-actions`.
- Overview composes persisted readiness, provider health, data freshness, brief, workflow,
  read-model signal cards, outcomes, action items, notifications, journal prompts, and quality
  warnings without triggering scans, LLMs, external delivery, or broker behavior.
- Quick actions allow only explicit backend-safe tasks: daily workflow, provider health refresh,
  daily brief generation, recent signal scoring, market memory refresh, and readiness run.
- Added command-center frontend overview components, overview/quick-action API clients, daily
  workflow helpers, and safe-copy utilities. Existing frontend composition remains fallback.
- Added docs: `apps/api/docs/workspace-overview.md`,
  `apps/api/docs/workspace-quick-actions.md`, and
  `apps/web/docs/command-center-workflow.md`.
- Verification: backend compileall passed; targeted Ruff passed; targeted
  `pytest app/tests/unit/test_workspace_actions.py` passed; web `npm run typecheck` passed; web
  `npm run lint` passed with pre-existing warnings outside this task.
- Important staging note: preserve the pre-existing unstaged `docs/project-state.md` deletion; stage
  only the new project-state hunk for this task.
- Added a new "Candles" section at the start of `README.md` clarifying candle data normalization and final-candle analysis source behavior.
- Replaced the initial README candle section with a Mermaid diagram showing candle ingestion/normalization/consumption flow.
- Updated top README candle diagram to a trading-candle flow (OHLCV bucketing, body/wick, bullish/bearish classification) instead of generic ingestion flow.
- Replaced Mermaid flowchart with an inline SVG candlestick graphic in README so the top 
- Updated README top candle section to an inline SVG candlestick chart so the opening README visual is rendered as real trading candles instead of Mermaid flow nodes.

## Modern Motion UI Rollout Loading Polish

- Next hardening step completed for production-grade route-level loading:
  - Added `loading.tsx` for major remaining routes under `apps/web/app/*`:
    `journal`, `notifications`, `review/outcomes`, `quality`, `readiness`, `setup`, `data/onboarding`,
    `equity-research`, `preferences/strategy`, `demo`, `signals/[signalId]`, `symbols/[symbolId]`,
    and `journal/[entryId]`.
  - All new route loading states use `AppShell` with `ShimmerSkeleton` placeholders and no backend/data
    contract changes.
  - Updated `apps/web/docs/motion-ui.md` manifest with loading-route coverage and rollout notes.
  - User request remains documentation-first; no test/build commands were run in this pass.

## Modern Motion UI Rollout Loading Shell Consolidation

- Added `apps/web/src/components/layout/RouteLoadingShell.tsx` to centralize `AppShell` + loading shell
  composition for all route-level suspense boundaries.
- Migrated all existing route-level loading files to the shared shell, including global fallback:
  - `apps/web/app/loading.tsx`
  - `apps/web/app/brief/loading.tsx`
  - `apps/web/app/command-center/loading.tsx`
  - `apps/web/app/dashboard/loading.tsx`
  - `apps/web/app/data/onboarding/loading.tsx`
  - `apps/web/app/demo/loading.tsx`
  - `apps/web/app/equity-research/loading.tsx`
  - `apps/web/app/journal/loading.tsx`
  - `apps/web/app/journal/[entryId]/loading.tsx`
  - `apps/web/app/notifications/loading.tsx`
  - `apps/web/app/onboarding/loading.tsx`
  - `apps/web/app/preferences/strategy/loading.tsx`
  - `apps/web/app/quality/loading.tsx`
  - `apps/web/app/readiness/loading.tsx`
  - `apps/web/app/review/outcomes/loading.tsx`
  - `apps/web/app/setup/loading.tsx`
  - `apps/web/app/signals/[signalId]/loading.tsx`
  - `apps/web/app/symbols/[symbolId]/loading.tsx`
  - `apps/web/app/triage/loading.tsx`
- Updated `apps/web/docs/motion-ui.md` with the shared shell manifest entry and rollout note.
- No backend contracts, endpoints, or UI safety language were changed.

## Modern Motion UI Rollout Scanner Loading Boundary

- Added `apps/web/app/scanner/loading.tsx` using `RouteLoadingShell` and `ShimmerSkeleton` for
  deterministic scan-flow fallback UI during suspense and transitions.
- Included `scanner` in the motion rollout loading matrix for consistency with route-level
  suspense governance.
- Updated `apps/web/docs/motion-ui.md` and `docs/project-state.md` with completion notes.
- No backend calls or route contracts were changed.
- Replaced the top README candlestick visual with the linked PNG image: https://png.pngtree.com/png-clipart/20250227/original/pngtree-trading-candlestick-chart-pattern-with-sell-buy-indicator-in-red-green-png-image_20522223.png

## Modern Motion UI Rollout Scanner Reveal Polish

- Applied staged, density-aware `AnimatedListItem` reveals in `apps/web/app/scanner/page.tsx` for:
  - hero block
  - preset/gallery and control modules
  - workflow/result panels
  - signal list and failure/error states
- Added production-grade polish sequencing without changing data composition or backend call behavior.
- Updated `apps/web/docs/motion-ui.md` rollout notes to record scanner row/panel reveal sequencing.
- Restored the README candlestick section and inserted the exact linked image directly under the badge block.

- [Motion UI Rollout – production-grade route reveal parity]
- Added section-level and panel/list-level motion wrappers to remaining product route pages using `@/lib/ui/motion` without behavior changes.
- Preserved non-advisory/read-only posture, fallback composition, accessibility states, and reduced-motion behavior.
- Updated `apps/web/docs/motion-ui.md` with a production-step completion note, route parity manifest, and manual verification checklist.
- Cleaned onboarding route import path to keep `motion` primitives imported from one stable public API entry.
- No test/build commands run in this task per user request.

- [Motion UI Rollout – primitive interaction harmonization]
- Hardened shared primitives in `apps/web/src/components/ui`: `Card`, `MutedCard`, `Surface`, `MetricCard`, `Badge`, and `Skeleton`.
- Added optional interactive focus-safe affordance props/classing where applicable and preserved static behavior defaults.
- Documented this production hardening pass in `apps/web/docs/motion-ui.md`.
- No tests/builds run per instruction.

## Modern Motion UI Rollout Interaction Hardening

- Added shared interactive token `MOTION_INTERACTIVE_CLASS` in `apps/web/src/components/ui/motion.tsx` and re-exported it from `apps/web/src/lib/ui/motion.ts`.
- Applied interactive polish + explicit `focus-visible` treatment to command-center and triage interactive rows/links without changing data flow.
- Updated `apps/web/src/components/layout/RouteLoadingShell.tsx` to pass optional workspace context through to `AppShell`.
- Updated `apps/web/docs/motion-ui.md` and `docs/project-state.md` with production-step notes.
- Kept safety posture and fallback behavior unchanged.
- No test/build commands run in this pass, per instruction.

## Motion UI Rollout Interaction Hardening – Commit Push Step

- Follow-up completed by staging and committing the interaction-hardening polish pass with shared `MOTION_INTERACTIVE_CLASS` usage in command-center and triage, plus `RouteLoadingShell` workspace context propagation.
- Kept `README.md` untouched to avoid mixing unrelated docs with this commit.
- Push requested to `origin main` after commit.

## Motion UI Rollout – Shared Primitive Interaction Consolidation

- Applied shared interactive motion token (`MOTION_INTERACTIVE_CLASS`) to core primitives to complete the interaction consolidation phase: `Card`, `Surface`, `Badge`, and `Button` now draw interactive focus-visible/hocus-lift behavior from one token.
- No backend, API contract, routing, or data-flow behavior was changed.
- Focus is on maintainable, tokenized interaction behavior in shared UI primitives plus documentation updates in `apps/web/docs/motion-ui.md` and durable notes in `docs/project-state.md`.
- Committed and pushed README top candles section update with the provided candlestick image link in commit `b75d0b1`.

## Motion UI Rollout – Legacy Helper Migration Enforcement

- Added dev-only one-time warnings inside `apps/web/src/components/ui/motion.tsx` for legacy helper usage (`motionRevealClass`, `motionRevealStyle`) to surface migration debt during UI integration reviews.
- Updated `apps/web/docs/motion-ui.md` with the production migration gate and runtime warning behavior for compatibility APIs.
- Updated durable notes in `docs/project-state.md` for governance and enforcement posture.
- No backend, API contract, test, or build changes in this pass; changes are code-only and documentation-only as requested.

## Motion UI Rollout – Production Route Audit Automation

- Added `apps/web/scripts/motion-rollout-audit.mjs` and new npm script `motion:rollout-audit` in `apps/web/package.json` to validate route-level motion wrappers and helper usage.
- Updated motion UI governance docs and project-state memory to record the rollout audit automation and pre-merge usage pattern.
- No backend/API contract changes in this pass; code changes are isolated to motion governance tooling and documentation.

## Modern Motion UI Rollout – Readiness + Review Route Depth

- Completed compact staggered reveal pass over remaining readiness and outcome-review surfaces:
  - `apps/web/src/components/readiness/ReadinessChecklist.tsx`
  - `apps/web/src/components/readiness/ReadinessRemediationPanel.tsx`
  - `apps/web/src/components/readiness/ReadinessBlockers.tsx`
  - `apps/web/src/components/review/OutcomeReviewQueue.tsx`
  - `apps/web/src/components/review/OutcomeReviewErrorState.tsx`
  - `apps/web/src/components/review/PatternDegradationPanel.tsx`
  - `apps/web/src/components/review/ProfileReliabilityPanel.tsx`
  - `apps/web/src/components/review/JournalPromptPanel.tsx`
  - `apps/web/src/components/outcome-review/OutcomeReviewQueueTable.tsx`
  - `apps/web/src/components/outcome-review/OutcomeReviewInsights.tsx`
- Reused the shared public motion API only (`AnimatedListItem`, `motionCardClass`, `motionRevealDensityStyle`, `motionRevealPresetClass`) and preserved existing contracts.
- Fixed local structure issue in `ReadinessRemediationPanel` by normalizing motion wrapper composition around links.
- Kept scope strictly code + docs only: no tests/builds executed.

## Modern Motion UI Rollout – Setup Review/Detail Reveal Deepening

- Expanded setup review and setup detail surfaces with staged row/panel reveal motion while preserving read-only behavior:
  - `apps/web/src/components/setup-review/SetupReviewSection.tsx`
  - `apps/web/src/components/setup-review/SetupReviewHeader.tsx`
  - `apps/web/src/components/setup-review/SetupContextReviewPanel.tsx`
  - `apps/web/src/components/setup-review/SetupEvidenceReviewPanel.tsx`
  - `apps/web/src/components/setup-review/SetupHistoricalReviewPanel.tsx`
  - `apps/web/src/components/setup-review/SetupWaitAvoidReviewPanel.tsx`
  - `apps/web/src/components/setup-review/SetupIntelligenceContextPanel.tsx`
  - `apps/web/src/components/setup-review/SetupReasoningReviewPanel.tsx`
  - `apps/web/src/components/setup-review/SetupAuditReviewPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupDetailView.tsx`
  - `apps/web/src/components/setup-detail/SetupVisualPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupConflictPanel.tsx`
  - `apps/web/src/components/setup-detail/SetupJournalPanel.tsx`
- Added compact list reveal sequencing in high-density content blocks and kept section-level staging in `SetupDetailView`.
- Updated `apps/web/docs/motion-ui.md` with this production step and left backend/API/data composition untouched.
- Scope remained code + documentation only; no test/build commands were run.

## Go Market Worker – Live Reconnect Jitter Hardening

- Added bounded reconnect jitter support to live websocket retry behavior in
  `apps/go/market-worker/internal/live/service.go`.
- Added config knob `MARKET_WORKER_LIVE_STREAM_RECONNECT_JITTER_PERCENT` in
  `apps/go/market-worker/internal/config/config.go` with validation and defaults.
- Added inspect visibility for `liveStreamReconnectJitterPercent` in
  `apps/go/market-worker/cmd/market-worker/main.go`.
- Documented jitter behavior in `apps/go/market-worker/README.md` and
  `apps/go/market-worker/OPERATIONS.md`.
- No tests/build commands were run in this pass, per instruction.

## Go Market Worker – Live Websocket Reconnect Resilience

- Added production-grade bounded exponential reconnect behavior in
  `apps/go/market-worker/internal/live/service.go` for Binance websocket streaming failures.
- Added new config knob:
  `MARKET_WORKER_LIVE_STREAM_MAX_RECONNECT_SECONDS` in
  `apps/go/market-worker/internal/config/config.go` and validated that it is a valid positive cap.
- Updated inspect output in `apps/go/market-worker/cmd/market-worker/main.go` with
  `liveStreamMaxReconnectSeconds` for live observability.
- Documented the reconnection strategy and max cap behavior in
  `apps/go/market-worker/README.md` and `apps/go/market-worker/OPERATIONS.md`.
- No test/build commands were run in this pass, per instruction.

## Equity Data External Provider Fetches

- Started from a clean `main`; there was no pre-existing local work to commit before this pass.
- Added opt-in environment-backed provider secret resolution:
  - `EQUITY_DATA_ENV_SECRET_RESOLUTION_ENABLED=false` by default;
  - supported `secret_ref` formats are `env:NAME`, `env-json:NAME`, and
    `env-pair:ALPACA_KEY_ID,ALPACA_SECRET_KEY`;
  - secret material is passed only in memory to provider adapters and is not stored in request,
    operation, or error payloads.
- Implemented read-only external equity provider adapters:
  - Polygon universe import, ticker metadata lookup, financial ratio/fundamentals snapshot, and
    earnings calendar context;
  - Alpaca asset universe import and asset metadata lookup only.
- Added runtime settings:
  - `POLYGON_REST_BASE_URL`;
  - `ALPACA_TRADING_BASE_URL`.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/.env.example`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - touched backend Python files passed `py_compile` syntax checks via the API virtualenv;
  - no tests, lint, typecheck, or build commands were run per user instruction.

## Equity Data Provider Resilience And Pagination

- Started from a clean `main`; there was no current local work to commit before this pass.
- Added shared provider HTTP retry behavior for transient `429` and `5xx` failures:
  - `EQUITY_DATA_PROVIDER_RETRY_ATTEMPTS`;
  - `EQUITY_DATA_PROVIDER_RETRY_BACKOFF_SECONDS`;
  - `Retry-After` is honored up to 60 seconds when present.
- Added bounded provider pagination:
  - `EQUITY_DATA_PROVIDER_MAX_PAGES`;
  - Polygon universe import now follows only the provider cursor value from `next_url`, never the
    raw URL itself;
  - callers can request a lower `filters.maxPages`/`filters.max_pages`;
  - truncated provider imports record a `polygon_pagination_truncated` warning and
    `truncated=true` summary metadata.
- Updated docs and durable memory:
  - `apps/api/docs/equity-data.md`;
  - `apps/api/.env.example`;
  - `docs/project-state.md`.
- Verification:
  - `git diff --check` passed;
  - touched backend Python files passed `py_compile` syntax checks via the API virtualenv;
  - no tests, lint, typecheck, or build commands were run per user instruction.
