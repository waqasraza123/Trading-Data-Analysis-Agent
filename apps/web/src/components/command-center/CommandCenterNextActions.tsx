import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { AnimatedListItem, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterNextActions({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Next backend-safe actions" eyebrow="Workflow" className={motionRevealPresetClass("scale-subtle")}>
          {data.nextActions.length === 0 ? (
            <p className="text-sm text-slate-500">{data.sectionStatuses.nextActions.message}</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {data.nextActions.map((item, index) => (
                <AnimatedListItem key={item.id} as="article" preset="scale-subtle" style={motionRevealDensityStyle(index, "compact")}>
                  <Link
                    href={item.href}
                    className={`rounded-lg border border-[var(--line)] p-4 transition ${motionCardClass} ${MOTION_INTERACTIVE_CLASS}`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-[var(--strong)]">{item.label}</p>
                      <Badge value={item.source} tone={item.tone} />
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
                  </Link>
                </AnimatedListItem>
              ))}
        </div>
      )}
    </Panel>
  );
}
