import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { MOTION_INTERACTIVE_CLASS } from "@/lib/ui/motion";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterAvoidPanel({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Avoid / no directional signal" eyebrow="Conditions">
          {data.avoidItems.length === 0 ? (
            <p className="text-sm text-slate-500">{data.sectionStatuses.avoidItems.message}</p>
          ) : (
            <div className="space-y-3">
              {data.avoidItems.map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`block rounded-lg border border-[var(--line)] p-3 transition hover:bg-slate-50 dark:hover:bg-slate-900 ${MOTION_INTERACTIVE_CLASS}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="text-sm font-semibold text-[var(--strong)]">
                  {item.symbol}
                  {item.timeframe ? ` ${item.timeframe}` : ""}
                </p>
                <Badge value={item.condition} tone={item.tone} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}
