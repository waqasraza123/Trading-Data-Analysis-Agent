import type { ProviderHealthPrepareGapRecoveryResponse } from "@/lib/provider-health/types";
import { ProviderHealthEmptyState } from "./ProviderHealthEmptyState";

type GapRecoveryPanelProps = {
  recovery: ProviderHealthPrepareGapRecoveryResponse | null;
};

export function GapRecoveryPanel({ recovery }: GapRecoveryPanelProps) {
  if (!recovery) {
    return (
      <ProviderHealthEmptyState
        title="No recovery plan prepared"
        message="Prepare recovery plan from a symbol and timeframe row when missing candles are present."
      />
    );
  }

  return (
    <div className="rounded-lg border border-[var(--line)] p-4">
      <p className="font-semibold text-[var(--strong)]">Recovery plan needed</p>
      <p className="mt-2 text-sm text-slate-500">
        {recovery.recovery_plan?.summary || "No missing candles were detected for this snapshot."}
      </p>
      <p className="mt-2 text-xs text-slate-500">
        Prepared {recovery.preparation?.prepared_request_count ?? 0} provider polling requests.
      </p>
    </div>
  );
}
