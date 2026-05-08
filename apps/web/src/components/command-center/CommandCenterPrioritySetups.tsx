import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterPrioritySetups({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Review first" eyebrow="Priority setups">
          {data.reviewFirst.length === 0 ? (
            <p className="text-sm text-slate-500">{data.sectionStatuses.reviewFirst.message}</p>
          ) : (
            <div className="grid gap-3 xl:grid-cols-2">
              {data.reviewFirst.map((item) => (
                <Link
                  key={item.signalId}
                  href={item.href}
                  className={`rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 transition hover:shadow-soft ${MOTION_INTERACTIVE_CLASS}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-base font-semibold text-[var(--strong)]">{item.symbol}</p>
                  <p className="text-sm text-slate-500">{item.timeframe}</p>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  {item.reviewPriorityLabel && <Badge value={item.reviewPriorityLabel} tone="info" />}
                  <Badge value={item.mainReason} tone="good" />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <Badge value={item.bias} />
                <Badge value={item.confidenceLabel} tone="info" />
                <Badge value={item.setupQualityLabel} tone="good" />
              </div>
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}
