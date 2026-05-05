import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { ButtonLink } from "@/components/ui/Button";
import { MetricCard } from "@/components/ui/MetricCard";
import type { CommandCenterData } from "@/lib/command-center/types";

export function CommandCenterFreshnessPanel({ data }: { data: CommandCenterData }) {
  return (
    <Panel title="Data readiness" eyebrow="Freshness">
      <div className="mb-4 grid grid-cols-2 gap-3">
        <MetricCard label="Data fresh" value={data.summary.freshSymbolCount} />
        <MetricCard label="Data stale" value={data.summary.staleOrDegradedCount} />
        <MetricCard label="Missing candles" value={data.summary.missingCandleCount} />
        <MetricCard label="Polling failed" value={data.summary.providerFailureCount} />
      </div>
      {data.dataReadiness.length === 0 ? (
        <p className="text-sm text-slate-500">{data.sectionStatuses.dataReadiness.message}</p>
      ) : (
        <div className="space-y-3">
          {data.dataReadiness.map((item) => (
            <Link key={item.id} href={item.href} className="block rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-3 transition hover:-translate-y-0.5 hover:shadow-soft">
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
      <ButtonLink className="mt-4" href={data.workspace ? `/data/onboarding?workspaceId=${data.workspace.id}` : "/data/onboarding"}>
        Review data freshness
      </ButtonLink>
    </Panel>
  );
}
