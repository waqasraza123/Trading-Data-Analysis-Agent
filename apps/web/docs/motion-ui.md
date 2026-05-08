# Motion UI System (Tailwind/CSS, No Motion Library)

This document defines the conservative animation layer used by the web product and the approved API for adding or adjusting motion behavior.

## Principles

- Keep animation low-risk and CSS-first.
- Preserve existing page behavior and data flow.
- Keep all routes read-only and non-advisory.
- Respect reduced-motion preferences.
- Use motion only for rhythm and progressive disclosure, not for critical-state signaling.

## File Map

- Foundation: `src/components/ui/motion.tsx`
- Re-exports: `src/lib/ui/motion.ts`
- Global keyframes/tokens: `app/globals.css`
- Optional animation utilities: `tailwind.config.ts`
- Route entry usage: all product routes under `app/*/page.tsx` and major route components in `src/components`

## Production Motion Profiles

The motion system now exposes compact/default/comfortable density profiles so teams can keep cadence consistent across high-density lists and heavier layouts.

- `compact`: `scale-subtle`, 30ms stagger
- `regular`: `fade-up`, 45ms stagger
- `comfortable`: `fade-up`, 60ms stagger

Defaults and helpers:

- `DEFAULT_MOTION_REVEAL_STEP_MS = 45`
- `COMFORT_MOTION_REVEAL_STEP_MS = 60`
- `MOTION_REVEAL_PROFILES`
- `motionRevealProfileStyle(index, profile?)`
- `motionRevealDensityStyle(index, "compact" | "regular" | "comfortable", durationMs?)`

## Import policy

- Use only `@/lib/ui/motion` for callsites.
- Reserve `@/components/ui/motion` for the implementation file and local unit-level co-location if absolutely required.
- This keeps app and component code consistent with the public API boundary and avoids mixed import patterns.

## Public Motion Types

- `MotionPreset` values:
  - `fade-up`
  - `fade-in`
  - `scale-subtle`
  - `none`
- `MotionRevealDensity` values:
  - `compact`
  - `regular`
  - `comfortable`
- `MotionRevealProfile`
- `MotionVariant` values (legacy migration path preserved):
  - `up` → `fade-up`
  - `scale` → `scale-subtle`
  - `fade` → `fade-in`
- `AnimateChildrenProps`
- `AnimateListItemProps`
- `MotionRevealStyle`
- `MotionRevealDensity`
- `MotionRevealProfile`

`AnimateChildrenProps` and `AnimateListItemProps` support:

- `preset?: MotionPreset`
- `delayMs?: number`
- `durationMs?: number`
- `staggerMs?: number` (list items)
- `style?: MotionRevealStyle`

## Usage

### Page/section entry

```tsx
import { AnimatedSection } from "@/lib/ui/motion";

export function PageBlock() {
  return (
    <AnimatedSection as="section" className="rounded-xl p-4">
      {/* normal page content */}
    </AnimatedSection>
  );
}
```

### Staggered list/panel reveal

```tsx
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";

function SignalList({ items }: { items: { id: string }[] }) {
  return (
    <div>
      {items.map((item, index) => (
        <AnimatedListItem
          key={item.id}
          index={index}
          as="section"
          style={motionRevealDensityStyle(index, "compact")}
          preset="scale-subtle"
        >
          ...
        </AnimatedListItem>
      ))}
    </div>
  );
}
```

### Class/style helpers (public API + migration posture)

- `motionRevealPresetClass("fade-up" | "fade-in" | "scale-subtle" | "none")`
- `motionRevealDensityStyle(index, density?, durationMs?)`
- `motionRevealProfileStyle(index, profile?)`
- `motionCardClass`
- `motionRevealClass("up" | "scale" | "fade")` remains available for compatibility only.

### Migration gate for production work

- New components must not introduce new `motionRevealClass` calls.
- New components should prefer preset + density/profile style helpers:
  - `motionRevealPresetClass` for class-level motion class selection
  - `motionRevealDensityStyle` for list/grid density
  - `motionRevealProfileStyle` for tuned per-surface profiles
- `motionRevealClass` and `motionRevealStyle` are retained as compatibility APIs and must only be used when migrating older surfaces.
- Production runtime now emits a one-time dev warning when compatibility APIs are used, helping teams migrate existing surfaces without behavior changes while preventing silent reversion.

## Defaults and tuning

- `BASE_MOTION_DELAY_MS = 60`
- `BASE_MOTION_DURATION_MS = 560`
- `DEFAULT_MOTION_PRESET = "fade-up"`
- `MOTION_PRESETS = ["fade-up", "fade-in", "scale-subtle", "none"]`
- `MOTION_VARIANTS = ["up", "scale", "fade"]`
- `DEFAULT_MOTION_REVEAL_STEP_MS = 45`
- `COMFORT_MOTION_REVEAL_STEP_MS = 60`
- `MOTION_REVEAL_PROFILES`

When introducing new routes/panels, prefer:

- `fade-up` for section transitions and section headers.
- `scale-subtle` for card-like surfaces and panel rows.
- `fade-in` for lightweight chips, micro badges, and low-motion contexts.
- `none` when no animation is needed or for reduced-motion-only surfaces.

## Reduced motion

`@media (prefers-reduced-motion: reduce)` disables all reveal, shimmer, pulse, and hover-shift animations while keeping final opacity/geometry stable.

## Accessibility

- Keep focus states and keyboard-visible behaviors intact.
- Do not encode state meaning in motion alone.
- Preserve existing safe copy and labels.
- Keep interactive hover states bound to existing `hover`/`focus-visible` utility behavior.

## Adoption map

- `AppShell`, `PageContainer`, `Topbar`, `MobileNav`, `Sidebar` now share standard reveal surfaces.
- Shared page surfaces in `src/components/ui/*` (e.g., `PageHeader`, `Section`, `Card`, `MetricCard`, `Skeleton`, `Badge`) include motion-safe defaults.
- Route-level entry wrappers are applied across primary product routes.
- Route-level loading skeletons are now co-located in `app/*/loading.tsx` for major data-heavy surfaces.
- A shared `RouteLoadingShell` now centralizes shell + AppShell composition for all route loading boundaries.
- Added global fallback route loading at `app/loading.tsx` for any Next route without a route-specific loading boundary, ensuring consistent shell + shimmer behavior during Suspense transitions.
- Panel/list-level staggering is applied to high-density surfaces:
  - `command-center`
  - `brief`
  - `triage`
  - setup and signal detail pages through `SetupReviewView`

## Route-level rollout manifest

The following routes are included in the current motion rollout and should continue to preserve this sequence:

- `command-center` → full section entry + panel reveals on badge strip, panel grid, and list rows
- `dashboard` → metric and top-card reveal, key list transitions
- `triage` → column container and card-row reveal cadence
- `brief` → section entry + narrative/list block reveal sequence
- `scanner` → hero and panel reveals
- `quality` → header and dashboard metric list reveals
- `notifications` → list row and panel reveal
- `journal` → header + metric + journal row reveals
- `review/outcomes` → metric and outcome row reveals
- `readiness` → readiness panel reveal
- `onboarding` → onboarding step reveal and detail panels
- `setup` → checklist/list row reveal
- `signals/[signalId]` → setup review section and staggered section layout
- `symbols/[symbolId]` → symbol detail block and list reveals
- `data/onboarding` → workflow step panel reveals
- `equity-research` → panel row reveals for universe/scope data
- `preferences/strategy` → form and card reveals
- `demo` → action card and status block reveal

Keep the manifest in sync when adding new routes:

- Add a route entry to this list before shipping.
- Define the route's reveal density (`compact` for dense repeated rows, `comfortable` for large hero-first layouts, otherwise `regular`).
- Add an integration note under "Detailed rollout notes".

## Detailed rollout notes (Production step: loading shell consolidation)

- `Sidebar` and `MobileNav` migrated high-density navigation reveal timing to `motionRevealDensityStyle(index, "compact")`.
- `SignalTriageBoard`, `SignalTriageColumn`, `SignalTriageCard`, `CommandCenterCockpit`, and `BriefNarrative` now consume density-aware reveal styles for section/panel ordering and dense row reveals.
- Default section/panel reveals use `motionRevealDensityStyle(index)` to preserve baseline 45ms behavior while removing inline `motionRevealStyle(..., 45)` usage in active rollout surfaces.
- Shared loading placeholders now use `ShimmerSkeleton` across command-center, brief, triage, dashboard, chart, and onboarding loading surfaces to keep shimmer/pulse behavior centralized.
- `scanner/page.tsx` now applies staged `AnimatedListItem` reveals across hero, preset/workflow controls, right-column panels, and result/error blocks using compact/comfortable density for transition consistency.
- Added `RouteLoadingShell` under `src/components/layout/RouteLoadingShell.tsx` to centralize `AppShell` + route loading scaffolding, and migrated the full route loading matrix to this shared primitive:
  - `app/loading.tsx`
  - `app/brief/loading.tsx`
  - `app/command-center/loading.tsx`
  - `app/dashboard/loading.tsx`
  - `app/data/onboarding/loading.tsx`
  - `app/demo/loading.tsx`
  - `app/equity-research/loading.tsx`
  - `app/journal/loading.tsx`
  - `app/journal/[entryId]/loading.tsx`
  - `app/notifications/loading.tsx`
  - `app/onboarding/loading.tsx`
  - `app/preferences/strategy/loading.tsx`
  - `app/quality/loading.tsx`
  - `app/readiness/loading.tsx`
  - `app/review/outcomes/loading.tsx`
  - `app/setup/loading.tsx`
  - `app/signals/[signalId]/loading.tsx`
  - `app/symbols/[symbolId]/loading.tsx`
  - `app/triage/loading.tsx`
  - `app/scanner/loading.tsx`
- Added production loading shell coverage for additional routes with app-level suspense states:
  - `journal`
  - `notifications`
  - `review/outcomes`
  - `quality`
  - `readiness`
  - `setup`
  - `data/onboarding`
  - `equity-research`
  - `preferences/strategy`
  - `demo`
  - `signals/[signalId]`
  - `symbols/[symbolId]`
  - `journal/[entryId]`
  - `scanner`
- Motion core bug fix: `AnimatedSection` and `AnimatedListItem` now apply `motion-no-motion` for `preset="none"`, preserving existing animation settings while explicitly disabling reveal movement when callers opt out.
- This pass does not change route behavior, backend composition, or advisory/safety copy.

## Detailed rollout notes (Production step: full route reveal parity)

- Completed the next production-grade sweep across remaining product entry surfaces without changing data flow, API contracts, or advisory posture.
- Route-level wrappers now cover all listed product paths for section/page entry reveals:
  - `command-center`, `dashboard`, `triage`, `brief`, `scanner`, `quality`, `notifications`, `journal`, `review/outcomes`, `readiness`, `onboarding`, `setup`, `signals/[signalId]`, `symbols/[symbolId]`, `data/onboarding`, `equity-research`, `preferences/strategy`, `demo`.
- High-value panels and lists were staggered in:
  - `command-center`, `brief`, `triage`, `setup`, `signals/[signalId]`, and `symbols/[symbolId]`.
- Remaining route-level motion surfaces use profile-based density so large hero-first pages stay readable while dense tables retain calm pacing:
  - `comfortable` for hero and narrative pages, `compact` for dense rows, and `regular` for mixed layouts.
- Reduced-motion behavior and safe focus/hover semantics remain explicit in unchanged components while motion wrappers are added through reusable API surfaces from `@/lib/ui/motion`.

## Detailed rollout notes (Production step: rollout governance automation)

- Added `apps/web/scripts/motion-rollout-audit.mjs` plus manifest source-of-truth file:
  - `apps/web/scripts/motion-rollout-manifest.json`
- Added scripts:
  - `npm run motion:rollout-audit` (default gate mode)
  - `npm run motion:rollout-audit:json` (machine-readable JSON report)
  - `npm run motion:rollout-audit:strict` (alias for strict JSON contract-mode; no legacy/coverage overrides)
- The gate validates each listed route by:
  - requiring expected motion entry tokens (for example `AnimatedSection`)
  - requiring motion helper usage (`motionRevealDensityStyle`, `motionRevealPresetClass`, `motionRevealProfileStyle`, etc.)
  - rejecting direct imports from the legacy path `@/components/ui/motion` (enforcing the public `@/lib/ui/motion` API boundary)
  - rejecting `motionRevealClass` and `motionRevealStyle` usage by default, with a controlled opt-out flag `--allow-legacy`
- The manifest schema is now versioned and validated:
  - required fields: `route`, `page`, `requires`
  - optional `revealDensity` for page-level cadence metadata (`compact`, `regular`, `comfortable`)
  - manifest entry validation is included in JSON output and fails strict mode
- This check is intended as the motion rollout contract guard before PR merge and keeps implementation intent tied to the manifest.
- The script now also performs a route-coverage gate by scanning `apps/web/app/*/page.tsx` and verifying manifest parity.
  - `app/page.tsx` is intentionally exempt in `motion-rollout-manifest.json` via `exemptRoutes`.
  - If a new user-facing page is added, add it to the manifest and docs rollout map before merge.
- Recommended run from `apps/web` before merging route-level motion/layout edits:
  - `npm run motion:rollout-audit`
  - `npm run motion:rollout-audit -- --allow-legacy` (use only for legacy migration windows)
  - `npm run motion:rollout-audit:json`
  - `npm run motion:rollout-audit -- --allow-coverage-gaps` (for temporary unblock during phased migration)
  - `npm run motion:rollout-audit:strict`

## Detailed rollout notes (Production step: shell + primitive hardening)

- Completed the shell-level hardening pass for shared layout and control surfaces:
  - `AppShell` now applies a stable root reveal using shared density defaults.
  - `PageContainer` now composes section-level reveal behavior through profile-driven delay presets.
  - `Topbar`, `MobileNav`, and `Sidebar` receive explicit density-aware entry presets plus focused keyboard-safe ring treatment.
- Strengthened shared interactive primitives without changing behavior contracts:
  - `Button` now includes explicit focus-visible ring-offset treatment plus shared hover-lift motion token in the base class composition.
  - Existing hover and focus-visible patterns remain explicit and non-semantic for state signaling.

## Detailed rollout notes (Production step: primitive interaction harmonization)

- Extended motion-safe interaction polish across additional shared primitives in `src/components/ui`:
  - `Card` and `MutedCard` now apply a shared interactive focus-visible pattern and preserve pointer semantics when used as pressable surfaces.
  - `Surface` now applies the same focus-visible and hover-lift treatment for interactive usage.
  - `MetricCard` received an optional `interactive` prop with focus-visible token alignment.
  - `Badge` received an optional `interactive` prop for explicit keyboard-focus affordances.
  - `Skeleton` now defaults to `aria-hidden` to keep loading shimmer decorative and avoid unnecessary announcement during assistive reading.
- This step remains copy-safe and state-preserving: no backend contracts, data composition, or route-level navigation logic changed.

## Detailed rollout notes (Production step: interaction hardening)

- Added a reusable interactive motion-accessibility token:
  - `MOTION_INTERACTIVE_CLASS` now centralizes hover-lift + explicit `focus-visible` ring behavior for interactive links/buttons.
- Re-exported this token from `src/lib/ui/motion.ts` to keep command-center and triage usage aligned with the shared motion API.
- Applied consistent production-safe interaction treatment to command-center row/link surfaces while preserving existing behavior:
  - `CommandCenterCockpit`
  - `CommandCenterFreshnessPanel`
  - `CommandCenterMorningBrief`
  - `CommandCenterPrioritySetups`
  - `CommandCenterNavigationGrid`
  - `CommandCenterOutcomeReview`
  - `CommandCenterReadinessStrip`
  - `CommandCenterJournalPrompt`
  - `CommandCenterAvoidPanel`
  - `CommandCenterConfirmationPanel`
  - `CommandCenterNextActions`
  - `CommandCenterScanStatus`
  - `CommandCenterWorkflowStatus`
  - `CommandCenterQuickActions`
  - `CommandCenterDailyScanButton`
  - `SignalTriageCard`
- Updated `CommandCenterCockpitPrimitives.CockpitActionLink` and `RouteLoadingShell` to consume shared interaction and shell-context APIs without changing route semantics.
- This polish pass preserves non-advisory wording, workspace-aware shell composition, and does not alter service contracts, query shapes, or load/retry behavior.

## Detailed rollout notes (Production step: shell interaction harmonization)

- Applied `MOTION_INTERACTIVE_CLASS` to shared layout shell navigation controls so interactive behavior is now centrally consistent.
- Updated `apps/web/src/components/layout/Sidebar.tsx`:
  - Added interactive class composition on top-brand link and nav items.
  - Replaced duplicated inline `focus-visible` utilities with shared token usage while keeping active-state styles intact.
- Updated `apps/web/src/components/layout/MobileNav.tsx`:
  - Replaced duplicated inline `focus-visible` utilities with shared token usage for route pills.
- Added shared interactive class usage for workspace context controls:
  - Updated `apps/web/src/components/workspace/WorkspaceSelector.tsx` so the workspace picker input now uses `MOTION_INTERACTIVE_CLASS` for explicit focus-visible + motion-hover behavior.
- No API contracts, route semantics, payload shape, or safety posture changes.

## Detailed rollout notes (Production step: shared primitive interaction consolidation)

- Consolidated core interactive utility classes in shared primitives to remove remaining ad-hoc focus-visible definitions while preserving existing hover behavior:
  - `apps/web/src/components/ui/Card.tsx`:
    - Replaced local focus-visible string constants with `MOTION_INTERACTIVE_CLASS` when `interactive={true}`.
  - `apps/web/src/components/ui/Surface.tsx`:
    - Replaced local focus-visible string constants with `MOTION_INTERACTIVE_CLASS` when `interactive={true}`.
  - `apps/web/src/components/ui/Badge.tsx`:
    - Replaced inline focus-visible utilities in interactive badge state with `MOTION_INTERACTIVE_CLASS`.
  - `apps/web/src/components/ui/Button.tsx`:
    - Replaced base button focus-visible utilities with `MOTION_INTERACTIVE_CLASS` in the shared class composition.
- `apps/web/src/components/ui/MetricCard.tsx`:
  - Replaced `motion-hover-lift` and inline `focus-visible` utility pair with `MOTION_INTERACTIVE_CLASS` while preserving interactive pointer behavior.
- `apps/web/src/components/ui/Section.tsx`:
  - Reused `MOTION_INTERACTIVE_CLASS` for section wrapper hover/focus polish consistency.
- `apps/web/src/components/ui/PageHeader.tsx`:
  - Applied `MOTION_INTERACTIVE_CLASS` in the animated page header container for consistent interaction styling.
- `MOTION_INTERACTIVE_CLASS` remains the single shared interaction source for hover/focus motion-safe polish in interactive primitives.
- No API contracts, data flow, or safety posture changes.

## Detailed rollout notes (Production step: interaction token normalization)

- Removed remaining direct `motion-hover-lift` class usage from non-interactive and legacy interactive call paths in:
  - `apps/web/src/components/ui/Card.tsx`
  - `apps/web/src/components/ui/Surface.tsx`
  - `apps/web/src/components/ui/Badge.tsx`
- Preserved interactive motion/focus behavior by keeping `MOTION_INTERACTIVE_CLASS` and pointer-only hover styles only on explicit interactive states.
- This pass avoids unintended hover/focus motion on static badges/surfaces while keeping keyboard-visible focus states explicit and unchanged.

## Detailed rollout notes (Production step: shared loading shell hardening)

- Consolidated loading skeleton behavior by routing `Skeleton` through `ShimmerSkeleton` in `apps/web/src/components/ui/Skeleton.tsx`.
- Added explicit accessibility defaults to `ShimmerSkeleton` (`aria-hidden` enabled by default) so loading placeholders remain decorative while still exposing an optional `ariaLabel`.
- Left route loading surfaces unchanged, preserving existing Suspense boundaries and fallback timing.

## Verification (manual, production-safe)

- Confirm route entry still lands with existing Suspense/load fallback behavior.
- Confirm no advisory/trading-action language changes were introduced.
- Confirm reduced-motion mode suppresses reveal, shimmer, and pulse movement.
- Confirm no additional data fetches or fallback behavior were introduced by animation wiring.

## Governance checklist

Use this as the PR-ready gate for any additional route.

- [ ] Route wrapped with `AnimatedSection` (or equivalent stable entry surface).
- [ ] High-density list or row blocks use `AnimatedListItem` + reusable reveal style helpers.
- [ ] Reduced-motion behavior verified by reading and confirming `prefers-reduced-motion: reduce` path in `app/globals.css`.
- [ ] Focus and hover states remain unchanged and explicit.
- [ ] No advisory copy changes introduced as part of rollout.
- [ ] New motion usage stays in `@/lib/ui/motion` (public API).
- [ ] Existing optional-endpoint fallback and data composition logic untouched.

## Governance

Use this API only for timing rhythm and visual polish.
Do not alter existing data orchestration, action dispatch, or backend contract behavior.
