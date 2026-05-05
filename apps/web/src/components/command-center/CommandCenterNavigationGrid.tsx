import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterNavigationGrid({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Daily workflow links" eyebrow="Navigation">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {data.navigationItems.map((item) => (
          <Link key={item.id} href={item.href} className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 transition hover:-translate-y-0.5 hover:shadow-soft">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="text-sm font-semibold text-[var(--strong)]">{item.label}</p>
              <Badge value="Open" tone={item.tone} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
          </Link>
        ))}
      </div>
    </Panel>
  );
}
