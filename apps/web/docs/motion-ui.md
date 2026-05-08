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
- `MotionVariant` values (legacy mapping preserved):
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

### Class/style helpers (legacy utility path)

- `motionRevealClass("up" | "scale" | "fade")`
- `motionRevealDensityStyle(index, density?, durationMs?)`
- `motionRevealProfileStyle(index, profile?)`
- `motionCardClass`

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

## Detailed rollout notes (Production step: density migration)

- `Sidebar` and `MobileNav` migrated high-density navigation reveal timing to `motionRevealDensityStyle(index, "compact")`.
- `SignalTriageBoard`, `SignalTriageColumn`, `SignalTriageCard`, `CommandCenterCockpit`, and `BriefNarrative` now consume density-aware reveal styles for section/panel ordering and dense row reveals.
- Default section/panel reveals use `motionRevealDensityStyle(index)` to preserve baseline 45ms behavior while removing inline `motionRevealStyle(..., 45)` usage in active rollout surfaces.
- Shared loading placeholders now use `ShimmerSkeleton` across command-center, brief, triage, dashboard, chart, and onboarding loading surfaces to keep shimmer/pulse behavior centralized.
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
- Motion core bug fix: `AnimatedSection` and `AnimatedListItem` now apply `motion-no-motion` for `preset="none"`, preserving existing animation settings while explicitly disabling reveal movement when callers opt out.
- This pass does not change route behavior, backend composition, or advisory/safety copy.

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
