import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { CommandCenterData } from "@/lib/command-center/types";
import { AnimatedListItem, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function CommandCenterOutcomeReview({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Outcome review" eyebrow="Observed outcomes" className={motionRevealPresetClass()}>
          {data.outcomeReview.length === 0 ? (
            <p className="text-sm text-slate-500">{data.sectionStatuses.outcomeReview.message}</p>
          ) : (
            <div className="space-y-3">
              {data.outcomeReview.map((item, index) => (
                <AnimatedListItem key={item.id} as="article" style={motionRevealDensityStyle(index, "compact")}>
                  <Link
                    href={item.href}
                    className={`block rounded-lg border border-[var(--line)] p-3 ${motionCardClass} ${MOTION_INTERACTIVE_CLASS}`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="text-sm font-semibold text-[var(--strong)]">
                        {item.symbol} {item.timeframe}
                      </p>
                      <Badge value={item.observationLabel} tone="info" />
                    </div>
                    <p className="mt-1 text-xs font-medium uppercase text-slate-500">{item.horizon}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
                  </Link>
                </AnimatedListItem>
              ))}
        </div>
      )}
    </Panel>
  );
}
