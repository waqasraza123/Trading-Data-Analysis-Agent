import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterFreshnessPanel({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Data readiness" eyebrow="Freshness">
      <div className="mb-4 grid grid-cols-2 gap-3">
        <Metric label="Data fresh" value={data.summary.freshSymbolCount} />
        <Metric label="Data stale" value={data.summary.staleOrDegradedCount} />
        <Metric label="Missing candles" value={data.summary.missingCandleCount} />
        <Metric label="Polling failed" value={data.summary.providerFailureCount} />
      </div>
      {data.dataReadiness.length === 0 ? (
        <p className="text-sm text-slate-500">{data.sectionStatuses.dataReadiness.message}</p>
      ) : (
        <div className="space-y-3">
          {data.dataReadiness.map((item) => (
            <Link key={item.id} href={item.href} className="block rounded-lg border border-[var(--line)] p-3 hover:bg-slate-50 dark:hover:bg-slate-900">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--strong)]">
                    {item.symbol}
                    {item.timeframe ? ` ${item.timeframe}` : ""}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">{item.detail}</p>
                </div>
                <Badge value={item.label} tone={item.tone} />
              </div>
            </Link>
          ))}
        </div>
      )}
      <Link className="mt-4 inline-flex rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-50 dark:hover:bg-slate-900" href={data.workspace ? `/data/onboarding?workspaceId=${data.workspace.id}` : "/data/onboarding"}>
        Review data freshness
      </Link>
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="muted-surface rounded-lg p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
