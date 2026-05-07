import { Panel } from "@/components/layout/panel";
import { formatContextDate, formatLargeNumber } from "@/lib/equity-data/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityMetadataPanel({ data }: { data: EquityResearchData }) {
  const metadata = data.selectedMetadata;
  return (
    <Panel title="Symbol metadata" eyebrow="Latest snapshot">
      {!metadata ? (
        <p className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 text-sm text-slate-500">
          Symbol metadata unavailable.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <Metric label="Company" value={metadata.company_name || metadata.ticker} />
          <Metric label="Exchange" value={metadata.exchange || "Unavailable"} />
          <Metric label="Sector" value={metadata.sector || "Unavailable"} />
          <Metric label="Industry" value={metadata.industry || "Unavailable"} />
          <Metric label="Market cap" value={formatLargeNumber(metadata.market_cap)} />
          <Metric label="Average volume" value={formatLargeNumber(metadata.average_volume)} />
          <Metric label="Provider" value={metadata.provider} />
          <Metric label="Snapshot" value={formatContextDate(metadata.snapshot_time)} />
        </div>
      )}
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
