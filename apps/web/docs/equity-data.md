# Equity Data UI

The `/equity-research` page now includes equity data setup and enrichment panels under the existing
research workflow. The UI is non-advisory and does not include broker execution, auto-trading,
account actions, direct buy/sell wording, or financial-advice language.

## Panels

- `EquityDataReadinessPanel`: shows whether stock universe, metadata, fundamentals, earnings, and
  catalyst context are available.
- `EquityDataProviderPanel`: lists provider capabilities and whether credential references are
  required or missing.
- `EquityUniverseImportPanel`: imports CSV-like ticker rows or the deterministic mock universe.
- `EquityUniverseFileImportPanel`: uploads CSV files with auto, sync, or queued import mode.
- `EquityDataOperationsPanel`: lists recent background operations with status, progress, counters,
  safe error summaries, and cancellation status when an operation has been stopped.
- `EquityEnrichmentJobsPanel`: queues metadata, fundamentals, earnings, and earnings catalyst
  operations for the selected research universe.
- `EquityMetadataPanel`: displays latest company, sector, industry, exchange, market cap, and
  average volume context.
- `EquityFundamentalsPanel`: displays latest fundamentals context where available.
- `EquityEarningsPanel`: fetches mock enrichment for the selected symbol and creates earnings
  catalyst context from stored events.
- `EquityProviderRequestHistory`: lists recent equity data provider requests and counts.

## Client Files

```txt
src/lib/api/equityData.ts
src/lib/equity-data/types.ts
src/lib/equity-data/labels.ts
src/components/equity-research/EquityDataOperationsPanel.tsx
src/components/equity-research/EquityEnrichmentJobsPanel.tsx
src/components/equity-research/EquityDataProviderPanel.tsx
src/components/equity-research/EquityUniverseFileImportPanel.tsx
src/components/equity-research/EquityUniverseImportPanel.tsx
src/components/equity-research/EquityMetadataPanel.tsx
src/components/equity-research/EquityFundamentalsPanel.tsx
src/components/equity-research/EquityEarningsPanel.tsx
src/components/equity-research/EquityProviderRequestHistory.tsx
src/components/equity-research/EquityDataReadinessPanel.tsx
```

## Data Flow

The equity research page loads provider capabilities, provider credential references, recent
provider requests, and enrichment snapshots for the selected candidate symbol or first selected
universe member. It also loads recent equity data operations. Optional endpoint failures are
rendered as unavailable state instead of crashing the page.

Import and enrichment actions call `/equity-data` APIs explicitly from client panels. Mock provider
actions work without credentials. External providers show provider configured or provider not
configured state based on backend settings and credential references.

The backend operation API supports idempotency keys for JSON operation submissions and
`POST /equity-data/operations/{operation_id}/cancel` for operator stops. The current UI lists the
resulting operation status and progress from the same operations endpoint; adding a visible cancel
button should call that endpoint through the shared mutation proxy and preserve the existing
non-advisory copy.

## CSV File Import

The file import panel sends `multipart/form-data` to
`POST /equity-data/operations/universe-import-file`. Accepted columns are `ticker` or `symbol`,
plus optional `name`, `exchange`, `sector`, `industry`, `currency`, `country`, and `asset_type`.
The backend trims fields, normalizes tickers uppercase, redacts credential-shaped columns, and does
not persist raw uploaded file bytes.

Run mode options:

- `auto`: synchronous for small files, queued for larger files.
- `sync`: request/response import for bounded small files.
- `queued`: parse and validate now, then run sanitized rows through the background worker.

## Safe Copy

The UI uses research-context language: import research universe, queue enrichment, provider
readiness, and operation progress. It does not present broker actions, copy trading, auto-trading,
external signal delivery, or financial-advice output.
