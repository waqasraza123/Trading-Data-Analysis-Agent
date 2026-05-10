# E2E Smoke Harness

The web app has a Playwright smoke harness under `apps/web/tests/e2e`.

It validates the daily cockpit without requiring:

- a running FastAPI process
- `DATABASE_URL`
- external market data providers
- LLM provider credentials
- notification delivery providers

## How It Works

`playwright.config.ts` starts two local servers:

- Next dev server on `http://127.0.0.1:3000`
- A deterministic mock API server on `http://127.0.0.1:4010`

The Next server receives:

```sh
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:4010
```

This matters because many pages fetch API data from Server Components. Browser route interception
cannot mock those server-side requests, so the harness uses the local mock API for page-load data
and keeps Playwright route helpers available for future client-only endpoints.

## Commands

From `apps/web`:

```sh
npm run test:e2e
npm run test:e2e:headed
npm run test:e2e:ui
```

CI runs the same smoke suite in `.github/workflows/web-ci.yml` after lint, typecheck, and build.

## Fixtures

Typed fixture payloads live in:

```txt
tests/e2e/fixtures/workspaceFixtures.ts
tests/e2e/fixtures/onboardingFixtures.ts
tests/e2e/fixtures/overviewFixtures.ts
tests/e2e/fixtures/apiMocks.ts
```

The mock server mirrors those contracts in `tests/e2e/helpers/mockApiServer.mjs`.
When backend response contracts change, update both the typed fixture and the mock server response
for that route.

## Coverage

The smoke suite covers:

- first-run onboarding empty, partial, ready, and backend-unavailable states
- workspace selector missing/default workspace behavior
- command-center readiness gate
- ready workspace overview payload rendering
- backend-safe quick-action success and unsupported-action states
- core daily route navigation
- populated demo daily dashboard workflow routes, including setup detail
- non-crashing states when optional dashboard modules are unavailable
- visible copy safety checks for critical pages

## Safe Copy

`tests/e2e/helpers/safeText.ts` centralizes visible banned phrase checks.
The scan reads visible page text only, not source code or docs.

Fixture copy must stay non-advisory and use review language such as:

- ready for deterministic analysis
- setup incomplete
- data fresh
- data stale
- command center ready
- run deterministic scan
- review setup context
- observation zone
- invalidation context
- outcome ready
- review recommended
- no directional signal

The harness must not introduce broker execution, auto-trading, copy trading, financial advice,
real external provider calls, notification delivery, hidden scans, hidden mutations, or directional
order instructions.
