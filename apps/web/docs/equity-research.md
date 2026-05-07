# Equity Research Page

The `/equity-research` page is a stock research workspace for deterministic swing setup candidate
review. It uses the FastAPI equity research APIs and keeps the frontend non-advisory: no broker
execution controls, order workflows, auto-trading, copy-trading, or direct action instructions.

## Page Capabilities

- Create and list workspace equity universes.
- Add existing stock symbols to a selected universe.
- Select deterministic swing scan profiles and timeframes.
- Run a backend swing scan against stored candles and persisted artifacts.
- View ranked swing setup candidates.
- Filter candidates by setup type, status, and quality label.
- Review component scores, evidence, review notes, and artifact links.
- Add manual catalyst context for universe symbols.

## Client Files

- `apps/web/app/equity-research/page.tsx`
- `apps/web/src/lib/api/equityResearch.ts`
- `apps/web/src/lib/equity-research/types.ts`
- `apps/web/src/lib/equity-research/labels.ts`
- `apps/web/src/components/equity-research/*`

## Data Flow

The page loads workspaces, stock symbols, equity universes, recent swing scan runs, candidates for
the selected scan, members for the selected universe, and catalyst context. Optional endpoint
failures render a warning section instead of crashing the route.

Running a swing scan posts a bounded request to `/equity-research/swing-scans`. The returned scan
run id is added to the route query string so the ranked candidate table and detail panel can refresh
around the persisted result.

## Safety Copy

The UI labels candidates as research candidates or swing setup candidates. It uses setup quality,
review notes, catalyst context, data freshness, and deterministic scan result language. It does not
use direct instruction wording or account-performance promises.
