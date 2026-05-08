import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { CommandCenterData } from "@/lib/command-center/types";
import { AnimatedListItem, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function CommandCenterNavigationGrid({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Daily workflow links" eyebrow="Navigation">
      <div className={`grid gap-3 md:grid-cols-2 xl:grid-cols-5 ${motionRevealPresetClass()}`}>
        {data.navigationItems.map((item, index) => (
          <AnimatedListItem key={item.id} as="article" style={motionRevealDensityStyle(index, "compact")}>
            <Link
              href={item.href}
              className={`block rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 ${motionCardClass} ${MOTION_INTERACTIVE_CLASS}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-sm font-semibold text-[var(--strong)]">{item.label}</p>
                <Badge value="Open" tone={item.tone} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </Link>
          </AnimatedListItem>
        ))}
      </div>
    </Panel>
  );
}
