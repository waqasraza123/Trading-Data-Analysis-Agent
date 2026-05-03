import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterMorningBrief({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="What changed?" eyebrow="Morning brief">
      {data.whatChanged.length === 0 ? (
        <p className="text-sm text-slate-500">{data.sectionStatuses.whatChanged.message}</p>
      ) : (
        <div className="space-y-3">
          {data.whatChanged.map((item) => (
            <Link
              key={item.id}
              href={item.href}
              className="block rounded-lg border border-[var(--line)] p-4 hover:bg-slate-50 dark:hover:bg-slate-900"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--strong)]">{item.title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
                </div>
                <Badge value={item.label} tone={item.tone} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </Panel>
  );
}
