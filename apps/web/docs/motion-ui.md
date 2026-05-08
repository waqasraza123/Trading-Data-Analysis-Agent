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
- `MotionVariant` values (legacy mapping preserved):
  - `up` → `fade-up`
  - `scale` → `scale-subtle`
  - `fade` → `fade-in`
- `AnimateChildrenProps`
- `AnimateListItemProps`
- `MotionRevealStyle`

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
import { AnimatedListItem, motionRevealStyle } from "@/lib/ui/motion";

function SignalList({ items }: { items: { id: string }[] }) {
  return (
    <div>
      {items.map((item, index) => (
        <AnimatedListItem
          key={item.id}
          index={index}
          as="section"
          style={motionRevealStyle(index, 45)}
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
- `motionRevealStyle(index, stepMs, durationMs?)`
- `motionCardClass`

## Defaults and tuning

- `BASE_MOTION_DELAY_MS = 60`
- `BASE_MOTION_DURATION_MS = 560`
- `DEFAULT_MOTION_PRESET = "fade-up"`
- `MOTION_PRESETS = ["fade-up", "fade-in", "scale-subtle", "none"]`
- `MOTION_VARIANTS = ["up", "scale", "fade"]`

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
- Panel/list-level staggering is applied to high-density surfaces:
  - `command-center`
  - `brief`
  - `triage`
  - setup and signal detail pages through `SetupReviewView`

## Governance

Use this API only for timing rhythm and visual polish.
Do not alter existing data orchestration, action dispatch, or backend contract behavior.
