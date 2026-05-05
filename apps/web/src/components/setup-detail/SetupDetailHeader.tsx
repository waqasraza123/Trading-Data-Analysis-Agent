import { Badge } from "@/components/status/badge";
import { BiasBadge } from "@/components/status/BiasBadge";
import { ConfidenceBadge } from "@/components/status/ConfidenceBadge";
import { FreshnessBadge } from "@/components/status/FreshnessBadge";
import { SetupQualityBadge } from "@/components/status/SetupQualityBadge";
import { PageHeader } from "@/components/ui/PageHeader";
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
      <PageHeader
        eyebrow="Full setup detail"
        title={header.symbol}
        description={header.summary}
        meta={
          <>
            <Badge value={header.timeframe} tone="info" />
            <BiasBadge value={header.bias} />
          </>
        }
        actions={
          <>
          <Badge value={header.pattern} tone="info" />
          <ConfidenceBadge value={header.confidenceLabel} />
          <SetupQualityBadge value={header.setupQualityLabel} />
        </>
        }
      />
      <dl className="mt-6 grid gap-4 text-sm md:grid-cols-5">
        <Detail label="Confidence" value={formatPercent(header.confidenceScore)} />
        <Detail label="Setup quality" value={formatPercent(header.setupQualityScore)} />
        <Detail label="Latest final candle" value={formatDateTime(header.latestFinalCandleTime)} />
        <div>
          <dt className="text-xs font-medium uppercase text-slate-500">Data freshness</dt>
          <dd className="mt-1"><FreshnessBadge value={setupLabel(header.dataFreshness)} /></dd>
        </div>
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
