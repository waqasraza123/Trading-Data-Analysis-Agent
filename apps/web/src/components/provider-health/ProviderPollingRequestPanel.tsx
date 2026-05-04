import { Badge } from "@/components/status/badge";
import type { ProviderHealthPrepareGapRecoveryResponse } from "@/lib/provider-health/types";
import { ProviderHealthEmptyState } from "./ProviderHealthEmptyState";

type ProviderPollingRequestPanelProps = {
  recovery: ProviderHealthPrepareGapRecoveryResponse | null;
};

export function ProviderPollingRequestPanel({ recovery }: ProviderPollingRequestPanelProps) {
  const requests = recovery?.preparation?.requests || [];
  if (requests.length === 0) {
    return (
      <ProviderHealthEmptyState
        title="No provider polling requests"
        message="Eligible recovery items will show prepare-only provider polling request metadata."
      />
    );
  }

  return (
    <div className="space-y-2">
      {requests.slice(0, 6).map((request) => (
        <div key={request.recovery_item_id} className="rounded-lg border border-[var(--line)] p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-[var(--strong)]">
              {request.provider || "Provider unavailable"} · {request.timeframe}
            </p>
            <Badge value={request.status} tone={request.provider ? "info" : "warning"} />
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Expected candles: {request.expected_candle_count}
          </p>
        </div>
      ))}
    </div>
  );
}
