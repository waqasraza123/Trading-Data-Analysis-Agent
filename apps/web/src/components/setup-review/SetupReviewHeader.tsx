import Link from "next/link";
import { Badge } from "@/components/status/badge";
import { BiasBadge } from "@/components/status/BiasBadge";
import { ConfidenceBadge } from "@/components/status/ConfidenceBadge";
import { SetupQualityBadge } from "@/components/status/SetupQualityBadge";
import { formatPercent } from "@/lib/formatting/numbers";
import type { SetupReviewMetric, SetupReviewModel } from "@/lib/setup-review/types";

type SetupReviewHeaderProps = {
  model: SetupReviewModel;
};

export function SetupReviewHeader({ model }: SetupReviewHeaderProps) {
  const header = model.header;

  return (
    <section className="sticky top-24 z-10 rounded-lg border border-[var(--line)] bg-[var(--panel)]/95 p-4 shadow-xl backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase text-slate-500">Setup review</p>
          <h1 className="mt-1 truncate text-2xl font-semibold text-[var(--strong)]">{header.symbol}</h1>
          <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600 dark:text-slate-300">{header.summary}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge value={header.timeframe} tone="info" />
            <BiasBadge value={header.bias} />
            <ConfidenceBadge value={header.confidenceLabel} />
            <SetupQualityBadge value={header.setupQualityLabel} />
            <Badge value={`Priority ${priorityText(model)}`} tone="warning" />
          </div>
        </div>
        <nav className="flex flex-wrap gap-2 text-sm font-semibold">
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-[var(--strong)]" href="#audit">Audit</Link>
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-[var(--strong)]" href="#reasoning">Report</Link>
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-[var(--strong)]" href="#journal">Journal</Link>
        </nav>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-6">
        {model.summaryMetrics.map((metric) => (
          <HeaderMetric key={metric.label} metric={metric} />
        ))}
      </div>
    </section>
  );
}

function HeaderMetric({ metric }: { metric: SetupReviewMetric }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{metric.label}</p>
      <p className="mt-1 truncate text-base font-semibold text-[var(--strong)]">{metric.value}</p>
      {metric.detail && <p className="mt-1 truncate text-xs text-slate-500">{metric.detail}</p>}
    </div>
  );
}

function priorityText(model: SetupReviewModel): string {
  const priorityMetric = model.summaryMetrics.find((metric) => metric.label === "Priority");
  return priorityMetric?.value || formatPercent(null);
}
