# Frontend Design System

The web app uses a small cockpit-oriented design system for read-only market intelligence pages.

## Components

- `src/components/ui/PageShell.tsx`: shared max width and responsive page padding.
- `src/components/ui/PageHeader.tsx`: route title, description, metadata badges, and route actions.
- `src/components/ui/Section.tsx` and `Card.tsx`: section cards and repeated content surfaces.
- `src/components/ui/Metric.tsx`: compact numeric and short-text summary cards.
- `src/components/ui/Badge.tsx` and `StatusPill.tsx`: normalized status labels and tones.
- `src/components/ui/EmptyState.tsx`, `ErrorState.tsx`, and `LoadingSkeleton.tsx`: shared state surfaces.
- `src/components/ui/Button.tsx`, `Tabs.tsx`, `FilterBar.tsx`, and `Timeline.tsx`: common interaction primitives.

## Status Badges

Status-specific wrappers live under `src/components/status`:

- `BiasBadge`: bullish, bearish, neutral, and no-directional labels.
- `ConfidenceBadge`: confidence labels and confidence-quality states.
- `FreshnessBadge`: final-candle and market-memory freshness.
- `DataQualityBadge`: candle/source/data quality labels.
- `SetupQualityBadge`: setup context quality labels.
- `OutcomeLabelBadge`: observed outcome labels.
- `ReadinessBadge`: product or decision-readiness labels.
- `PriorityBadge`: review priority labels.
- `WorkerStatusBadge`: runtime worker availability and run state.

Tone mapping lives in `src/lib/ui/statusStyles.ts`. Existing imports from `components/status/badge.tsx` remain supported as compatibility glue.

## Navigation

`src/lib/ui/navigation.ts` is the route registry for the daily cockpit:

- Command Center
- Brief
- Data
- Scanner
- Triage
- Quality
- Notifications
- Journal
- Review Outcomes
- Preferences

`AppShell` renders responsive top navigation from the registry and highlights active routes. `WorkflowLinks` uses the same registry and adds `workspaceId` when available.

## Safe Language

UI copy must stay read-only and non-advisory. Prefer:

- `review`, `observe`, `context`, `setup context`, and `review priority`
- `observation zone`, `invalidation context`, and `target context zone`
- `observed follow-through`, `observed reversal`, and `no follow-through observed`

Avoid order, account-result, certainty, and advice language. `src/lib/ui/safeCopy.ts` and `src/lib/ui/labels.ts` centralize fallback replacements for unsafe source labels.

## Page Conventions

- Route pages should render inside `AppShell`.
- Use `PageHeader` for the route title and workspace metadata.
- Use `Section` for page sections and repeated panels.
- Use `FilterBar` when query filters already exist.
- Use status-specific badges for domain labels instead of ad hoc badge tone logic.
- Use collapsible `details` blocks for long evidence, scenario, risk, or audit sections.
