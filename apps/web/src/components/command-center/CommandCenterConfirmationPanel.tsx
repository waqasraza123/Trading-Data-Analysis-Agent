import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { AnimatedListItem, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterConfirmationPanel({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Needs confirmation" eyebrow="Review state" className={motionRevealPresetClass()}>
          {data.needsConfirmation.length === 0 ? (
            <p className="text-sm text-slate-500">{data.sectionStatuses.needsConfirmation.message}</p>
          ) : (
            <div className="space-y-3">
              {data.needsConfirmation.map((item, index) => (
                <AnimatedListItem
                  key={item.id}
                  as="article"
                  preset="scale-subtle"
                  style={motionRevealDensityStyle(index, "compact")}
                >
                  <Link
                    href={item.href}
                    className={`block rounded-lg border border-[var(--line)] p-3 transition ${motionCardClass} ${MOTION_INTERACTIVE_CLASS}`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-[var(--strong)]">
                        {item.symbol} {item.timeframe}
                      </p>
                      <Badge value={item.label} tone="warning" />
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
                  </Link>
                </AnimatedListItem>
              ))}
        </div>
      )}
    </Panel>
  );
}
