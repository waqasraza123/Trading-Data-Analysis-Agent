import { MetricCard } from "@/components/layout/panel";
import type { ProviderHealthSummary } from "@/lib/provider-health/types";

type ProviderHealthSummaryCardsProps = {
  summary: ProviderHealthSummary | null;
};

export function ProviderHealthSummaryCards({ summary }: ProviderHealthSummaryCardsProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard
        label="Healthy sources"
        value={String(summary?.healthy_count ?? 0)}
        detail={`${summary?.total_snapshots ?? 0} checked`}
      />
      <MetricCard
        label="Data stale"
        value={String(summary?.stale_count ?? 0)}
        detail={`${summary?.delayed_count ?? 0} delayed`}
      />
      <MetricCard
        label="Missing candles"
        value={String(summary?.missing_candle_count ?? 0)}
        detail="Across checked scopes"
      />
      <MetricCard
        label="Ready"
        value={String(summary?.ready_for_deterministic_analysis_count ?? 0)}
        detail="Ready for deterministic analysis"
      />
    </div>
  );
}
