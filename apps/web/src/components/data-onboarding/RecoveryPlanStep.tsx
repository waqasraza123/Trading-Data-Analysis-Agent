import { Badge, toneForQuality } from "@/components/status/badge";
import type { GapDetectionRow, RecoveryPreparationRow } from "@/lib/data-onboarding/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { OnboardingEmptyState } from "./OnboardingEmptyState";

type RecoveryPlanStepProps = {
  rows: RecoveryPreparationRow[];
  gapRows: GapDetectionRow[];
  loadState: string;
  onPrepareRecovery: () => void;
};

export function RecoveryPlanStep({
  rows,
  gapRows,
  loadState,
  onPrepareRecovery,
}: RecoveryPlanStepProps) {
  const gapCount = gapRows.reduce((count, row) => count + row.items.length, 0);

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Step 5</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Recovery plan</h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Prepare provider polling metadata for eligible gaps. External provider fetches are not executed.
          </p>
        </div>
        <button
          type="button"
          disabled={gapCount === 0 || loadState === "loading"}
          onClick={onPrepareRecovery}
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {loadState === "loading" ? "Preparing" : "Prepare recovery plan"}
        </button>
      </div>
      {gapCount === 0 ? (
        <OnboardingEmptyState
          title="No recovery items"
          message="Run gap detection first. Complete data windows do not need a recovery plan."
        />
      ) : rows.length === 0 ? (
        <OnboardingEmptyState
          title="Recovery not prepared"
          message="Prepare recovery plan to see eligible provider polling requests and manual import items."
        />
      ) : (
        <div className="grid gap-4">
          {rows.map((row) => (
            <div key={row.gap.plan?.id || row.gap.health.target.symbol.id} className="rounded-lg border border-[var(--line)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">
                    {row.gap.health.target.symbol.symbol} · {row.gap.health.target.timeframe}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {row.preparation?.prepared_request_count ?? 0} prepared, {row.preparation?.skipped_request_count ?? 0} skipped
                  </p>
                </div>
                <Badge value="Prepare only" tone="info" />
              </div>
              {row.errors.length > 0 && <p className="mt-3 text-sm text-red-700 dark:text-red-200">{row.errors[0].message}</p>}
              {row.requests.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[820px] text-left text-sm">
                    <thead className="text-xs uppercase text-slate-500">
                      <tr>
                        <th className="border-b border-[var(--line)] px-3 py-2">Window</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Provider</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Symbol</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Expected</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {row.requests.map((request) => (
                        <tr key={request.recovery_item_id}>
                          <td className="border-b border-[var(--line)] px-3 py-3">
                            {formatDateTime(request.start_time)} to {formatDateTime(request.end_time)}
                          </td>
                          <td className="border-b border-[var(--line)] px-3 py-3">{request.provider || "Not available"}</td>
                          <td className="border-b border-[var(--line)] px-3 py-3">{request.provider_symbol || "Not available"}</td>
                          <td className="border-b border-[var(--line)] px-3 py-3">{request.expected_candle_count}</td>
                          <td className="border-b border-[var(--line)] px-3 py-3">
                            <Badge value={request.status} tone={toneForQuality(request.status)} />
                            {request.skip_reason && <p className="mt-1 text-xs text-slate-500">{request.skip_reason}</p>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
