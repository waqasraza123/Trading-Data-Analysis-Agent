import { MetricCard, Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { ScannerData } from "@/lib/scanner/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { statusTone } from "@/lib/scanner/labels";

export function ScannerStatusPanel({ data }: { data: ScannerData }) {
  const scanRunListingAvailable = false;

  return (
    <Panel
      title="Scanner status"
      eyebrow="Backend availability"
      action={<Badge value={data.apiBaseUrl} tone="neutral" />}
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Watchlists" value={String(data.watchlists.length)} detail="Workspace scanner lists" />
        <MetricCard label="Scan configs" value={String(data.scanConfigs.length)} detail={`${data.dueScanConfigs.length} due now`} />
        <MetricCard label="Symbols" value={String(data.symbols.length)} detail={`${data.dataSources.length} active sources`} />
        <MetricCard label="Last loaded" value={formatDateTime(data.lastUpdatedAt)} detail="Browser refresh reloads backend state" />
      </div>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <StatusLine label="API" value={data.health?.status || "unavailable"} />
        <StatusLine label="Worker" value={data.workerStatus?.status || "unavailable"} />
        <StatusLine label="Recent runs endpoint" value={scanRunListingAvailable ? "available" : "not exposed"} />
      </div>
    </Panel>
  );
}

function StatusLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="muted-surface flex items-center justify-between gap-3 rounded-2xl p-4">
      <span className="text-sm font-semibold text-[var(--text-muted)]">{label}</span>
      <Badge value={value} tone={statusTone(value)} />
    </div>
  );
}
