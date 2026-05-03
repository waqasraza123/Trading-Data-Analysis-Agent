import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { formatPercent } from "@/lib/formatting/numbers";
import { setupLabel } from "@/lib/setup-detail/labels";
import type { SetupDetailHeaderModel } from "@/lib/setup-detail/types";

type SetupDetailHeaderProps = {
  header: SetupDetailHeaderModel;
};

export function SetupDetailHeader({ header }: SetupDetailHeaderProps) {
  return (
    <section className="surface rounded-lg p-6">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="max-w-4xl">
          <p className="text-xs font-semibold uppercase text-slate-500">Full setup detail</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-[var(--strong)]">{header.symbol}</h1>
            <Badge value={header.timeframe} tone="info" />
            <Badge value={header.bias} tone={toneForBias(header.bias)} />
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{header.summary}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge value={header.pattern} tone="info" />
          <Badge value={header.confidenceLabel} tone={toneForQuality(header.confidenceLabel)} />
          <Badge value={header.setupQualityLabel} tone={toneForQuality(header.setupQualityLabel)} />
        </div>
      </div>
      <dl className="mt-6 grid gap-4 text-sm md:grid-cols-5">
        <Detail label="Confidence" value={formatPercent(header.confidenceScore)} />
        <Detail label="Setup quality" value={formatPercent(header.setupQualityScore)} />
        <Detail label="Latest final candle" value={formatDateTime(header.latestFinalCandleTime)} />
        <Detail label="Data freshness" value={setupLabel(header.dataFreshness)} />
        <Detail label="Product boundary" value="Review context only" />
      </dl>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}
