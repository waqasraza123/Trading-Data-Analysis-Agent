import { Panel } from "@/components/layout/panel";
import { formatContextDate, formatLargeNumber } from "@/lib/equity-data/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityFundamentalsPanel({ data }: { data: EquityResearchData }) {
  const fundamentals = data.selectedFundamentals;
  return (
    <Panel title="Fundamentals context" eyebrow="Latest snapshot">
      {!fundamentals ? (
        <p className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 text-sm text-slate-500">
          Fundamentals context unavailable.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          <Metric label="Average volume" value={formatLargeNumber(fundamentals.average_volume)} />
          <Metric label="Relative volume" value={fundamentals.relative_volume || "Unavailable"} />
          <Metric label="Beta" value={fundamentals.beta || "Unavailable"} />
          <Metric label="P/E" value={fundamentals.pe_ratio || "Unavailable"} />
          <Metric label="EPS" value={fundamentals.eps || "Unavailable"} />
          <Metric label="Free cash flow" value={formatLargeNumber(fundamentals.free_cash_flow)} />
          <Metric label="Provider" value={fundamentals.provider} />
          <Metric label="Snapshot" value={formatContextDate(fundamentals.snapshot_time)} />
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
