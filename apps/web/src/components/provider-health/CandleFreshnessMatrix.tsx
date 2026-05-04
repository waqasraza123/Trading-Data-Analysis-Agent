import { Badge } from "@/components/status/badge";
import { providerHealthTone } from "@/lib/provider-health/labels";
import type { ProviderHealthSnapshot } from "@/lib/provider-health/types";
import { ProviderHealthEmptyState } from "./ProviderHealthEmptyState";

type CandleFreshnessMatrixProps = {
  snapshots: ProviderHealthSnapshot[];
};

export function CandleFreshnessMatrix({ snapshots }: CandleFreshnessMatrixProps) {
  const scoped = snapshots.filter((snapshot) => snapshot.symbol_id && snapshot.timeframe);
  if (scoped.length === 0) {
    return (
      <ProviderHealthEmptyState
        title="No candle freshness matrix"
        message="Symbol and timeframe snapshots will appear after provider health refresh."
      />
    );
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {scoped.slice(0, 16).map((snapshot) => (
        <div key={snapshot.id} className="rounded-lg border border-[var(--line)] p-3">
          <div className="flex items-center justify-between gap-2">
            <p className="text-sm font-semibold text-[var(--strong)]">{snapshot.timeframe}</p>
            <Badge value={snapshot.freshness_label} tone={providerHealthTone(snapshot.freshness_label)} />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Missing candles: {snapshot.missing_candle_count}
          </p>
        </div>
      ))}
    </div>
  );
}
