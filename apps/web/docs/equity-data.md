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
src/components/equity-research/EquityDataProviderPanel.tsx
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
universe member. Optional endpoint failures are rendered as unavailable state instead of crashing
the page.

Import and enrichment actions call `/equity-data` APIs explicitly from client panels. Mock provider
actions work without credentials. External providers show provider configured or provider not
configured state based on backend settings and credential references.
