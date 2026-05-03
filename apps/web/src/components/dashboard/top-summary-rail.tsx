import { MetricCard } from "@/components/layout/panel";
import type { DashboardData } from "@/lib/api/dashboard";
import { formatInteger } from "@/lib/formatting/numbers";

export function TopSummaryRail({ data }: { data: DashboardData }) {
  const activeWatchlistCount = data.watchlists.filter(({ watchlist }) => watchlist.status === "active").length;
  const freshCount = data.memorySnapshots.filter((snapshot) => snapshot.freshness_label === "fresh").length;
  const degradedCount = data.memorySnapshots.filter(
    (snapshot) => snapshot.freshness_label !== "fresh" || snapshot.data_quality_label === "weak",
  ).length;
  const completedScanCount = data.scheduledScans.filter((scan) => Boolean(scan.last_run_at)).length;

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <MetricCard label="Active watchlists" value={formatInteger(activeWatchlistCount)} detail="Configured symbol groups" />
      <MetricCard label="Fresh symbols" value={formatInteger(freshCount)} detail="Market memory state" />
      <MetricCard label="Stale or degraded" value={formatInteger(degradedCount)} detail="Review recommended" />
      <MetricCard label="Completed scan configs" value={formatInteger(completedScanCount)} detail="Last-run timestamps" />
      <MetricCard label="Recent digest items" value={formatInteger(data.latestDigestItems.length)} detail="Compiled context rows" />
      <MetricCard label="Pending follow-up" value={formatInteger(data.dueActionItems.length)} detail="Backend action items" />
    </div>
  );
}
