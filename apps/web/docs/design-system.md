# Frontend Design System

The web app uses a Tailwind-native cockpit design system for read-only market intelligence pages. It is intentionally lightweight: no heavy UI framework, no broker/execution affordances, and no advisory copy.

## Visual Foundation

Global tokens live in `app/globals.css` and are exposed to Tailwind through `tailwind.config.ts`.

- `--background`, `--surface`, `--surface-muted`, `--surface-elevated`, `--border`, `--foreground`, and `--text-muted` define the app shell and cards.
- `--accent`, `--success`, `--warning`, `--danger`, and `--info` define status and action tones.
- `--shadow-soft`, `--shadow-panel`, and `--shadow-glow` define the cockpit depth model.
- `.surface`, `.muted-surface`, and `.premium-control` are the only shared global utility classes; prefer component props before adding more globals.

## Components

- `src/components/ui/Surface.tsx`, `Card.tsx`, `Section.tsx`, and `SectionHeader.tsx`: primary surfaces, cards, and panel headers.
- `src/components/ui/PageHeader.tsx` and `src/components/layout/PageContainer.tsx`: route headers and responsive page width.
- `src/components/ui/MetricCard.tsx`, `StatGrid.tsx`, `Badge.tsx`, and `StatusPill.tsx`: dense dashboard stats and status metadata.
- `src/components/ui/EmptyState.tsx`, `ErrorState.tsx`, `LoadingState.tsx`, and `Skeleton.tsx`: consistent loading and failure states.
- `src/components/ui/Button.tsx`, `Tabs.tsx`, `FilterBar.tsx`, `ActionBar.tsx`, `Timeline.tsx`, `Tooltip.tsx`, and `Divider.tsx`: shared interaction and layout primitives.

Compatibility exports remain for older imports such as `Metric`, `PageShell`, and `LoadingSkeleton`.

## App Shell

The shell lives under `src/components/layout/`:

- `AppShell.tsx`: wraps every app route with the cockpit frame.
- `Sidebar.tsx`: desktop route groups and active route state.
- `Topbar.tsx`: workspace context and API health indicator.
- `MobileNav.tsx`: mobile horizontal navigation.
- `WorkspaceSwitcher.tsx`: current workspace display.
- `PageContainer.tsx`: shared route content bounds.

`src/lib/ui/navigation.ts` is the route registry. Add routes there first, then use `navigationHref` or `WorkflowLinks` so workspace-aware URLs stay consistent.

## Status Badges

Status-specific wrappers live under `src/components/status`:

- `BiasBadge`: bullish, bearish, neutral, and no-directional labels.
- `ConfidenceBadge`: confidence labels and confidence-quality states.
- `FreshnessBadge`: final-candle and market-memory freshness.
- `DataQualityBadge`: candle/source/data quality labels.
- `SetupQualityBadge`: setup context quality labels.
- `OutcomeLabelBadge` and `OutcomeBadge`: observed outcome labels.
- `ReadinessBadge`: product or decision-readiness labels.
- `PriorityBadge`: review priority labels.
- `WorkerStatusBadge`: runtime worker availability and run state.

Tone mapping lives in `src/lib/ui/statusStyles.ts`. Existing imports from `components/status/badge.tsx` remain supported as compatibility glue. Prefer the domain badge wrappers over ad hoc tone mapping in page components.

## Safe Language

UI copy must stay read-only and non-advisory. Prefer:

- `review`, `observe`, `context`, `setup context`, and `review priority`
- `observation zone`, `invalidation context`, and `target context zone`
- `observed follow-through`, `observed reversal`, and `no follow-through observed`

Avoid direct order instructions, account-result claims, certainty claims, and advice language. `src/lib/ui/safeCopy.ts`, `src/lib/ui/safeLabels.ts`, and `src/lib/ui/labels.ts` centralize fallback replacements for unsafe source labels.

## Page Conventions

- Route pages should render inside `AppShell`.
- Use `PageHeader` or a feature-specific hero for the route title, workspace metadata, and safe workflow context.
- Use `Section`, `Card`, `Surface`, or feature-local panel primitives for repeated sections.
- Use `FilterBar` or feature-local filter shells when query filters already exist.
- Use status-specific badges for domain labels instead of ad hoc badge tone logic.
- Use collapsible `details` blocks for long evidence, scenario, risk, or audit sections.
- Keep feature-specific primitives small and local when a page needs a denser narrative layout, as with command center, brief, setup review, and outcome review.
