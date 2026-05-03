import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import type { ProviderHealthSnapshot } from "@/lib/provider-health/types";
import { ProviderHealthEmptyState } from "./ProviderHealthEmptyState";

type ProviderFailurePanelProps = {
  snapshots: ProviderHealthSnapshot[];
};

export function ProviderFailurePanel({ snapshots }: ProviderFailurePanelProps) {
  const failing = snapshots.filter(
    (snapshot) => snapshot.consecutive_failure_count > 0 || snapshot.latest_failed_poll_at,
  );

  if (failing.length === 0) {
    return (
      <ProviderHealthEmptyState
        title="No recent provider failures"
        message="Provider polling failures were not found in the current snapshots."
      />
    );
  }

  return (
    <div className="space-y-3">
      {failing.slice(0, 5).map((snapshot) => (
        <div key={snapshot.id} className="rounded-lg border border-[var(--line)] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="font-semibold text-[var(--strong)]">{snapshot.provider}</p>
              <p className="mt-1 text-sm text-slate-500">{snapshot.summary}</p>
            </div>
            <Badge value="Polling failed" tone="danger" />
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Latest failure {formatDateTime(snapshot.latest_failed_poll_at)}
          </p>
        </div>
      ))}
    </div>
  );
}
