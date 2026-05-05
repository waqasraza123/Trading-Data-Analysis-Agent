import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Badge } from "@/components/status/badge";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { statusTone } from "@/lib/scanner/labels";
import type { ScannerData, ScheduledScanRun } from "@/lib/scanner/types";

export function ScannerHero({ data }: { data: ScannerData }) {
  const activeWatchlists = data.watchlists.filter(({ watchlist }) => watchlist.status === "active");
  const activeScanConfigs = data.scanConfigs.filter((config) => config.status === "active");
  const latestRun = latestScanRun(data);
  const failedOrSkipped = latestRun ? latestRun.failed_count + latestRun.skipped_count : 0;
  const readyItems = data.watchlists.reduce(
    (count, entry) => count + entry.items.filter((item) => item.is_active).length,
    0,
  );
  const readinessLabel = data.failures.length > 0
    ? "Data degraded"
    : readyItems > 0 && data.dataSources.length > 0
      ? "Scan ready"
      : "Setup needed";

  return (
    <section className="overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--panel)] shadow-[var(--shadow-panel)]">
      <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={data.workspace?.name || "No workspace"} tone={data.workspace ? "info" : "warning"} />
            <Badge value={readinessLabel} tone={readinessLabel === "Scan ready" ? "good" : readinessLabel === "Setup needed" ? "warning" : "danger"} />
          </div>
          <div className="mt-5 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Scanner workflow
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-[var(--strong)] sm:text-4xl">
              Guided watchlist scans for deterministic analysis
            </h1>
            <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Configure watchlists, apply scan presets, run backend deterministic scans, and review
              completed scan output. This page does not connect brokers, send external messages, or
              provide financial advice.
            </p>
          </div>
          <div className="mt-6">
            <WorkflowLinks
              workspaceId={data.workspace?.id}
              targets={["commandCenter", "brief", "triage", "dataOnboarding", "quality", "journal"]}
            />
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <HeroMetric label="Watchlists configured" value={String(activeWatchlists.length)} detail={`${readyItems} active items`} />
            <HeroMetric label="Scan configs active" value={String(activeScanConfigs.length)} detail={`${data.dueScanConfigs.length} due now`} />
            <HeroMetric label="Latest scan run" value={latestRun ? latestRun.status : "None"} detail={latestRun ? formatRelativeTime(latestRun.completed_at || latestRun.started_at) : "Run a config to inspect details"} />
            <HeroMetric label="Failed or skipped" value={String(failedOrSkipped)} detail="Latest selected run" />
            <HeroMetric label="Data readiness" value={readinessLabel} detail={`${data.dataSources.length} active sources`} />
          </div>
        </div>
        <aside className="border-t border-[var(--line)] bg-[var(--panel-muted)] p-6 xl:border-l xl:border-t-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Current backend state
          </p>
          <div className="mt-4 grid gap-3">
            <StatusRow label="API" value={data.health?.status || "unavailable"} />
            <StatusRow label="Worker" value={data.workerStatus?.status || "unavailable"} />
            <StatusRow label="Last loaded" value={formatDateTime(data.lastUpdatedAt)} />
            <StatusRow label="Optional failures" value={data.failures.length > 0 ? `${data.failures.length} reported` : "None"} />
          </div>
        </aside>
      </div>
    </section>
  );
}

function HeroMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 truncate text-2xl font-semibold text-[var(--strong)]">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  );
}

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2">
      <span className="text-sm font-medium text-slate-500">{label}</span>
      <Badge value={value} tone={statusTone(value)} />
    </div>
  );
}

function latestScanRun(data: ScannerData): ScheduledScanRun | null {
  const runs = [...data.recentRuns, data.selectedRun].filter(
    (run): run is ScheduledScanRun => Boolean(run),
  );
  return runs.sort((left, right) => {
    const leftTime = new Date(left.completed_at || left.started_at || left.created_at || "").getTime();
    const rightTime = new Date(right.completed_at || right.started_at || right.created_at || "").getTime();
    return rightTime - leftTime;
  })[0] || null;
}
