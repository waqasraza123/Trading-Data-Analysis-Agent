import { Badge, toneForQuality } from "@/components/status/badge";
import type { DataHealthRow, GapDetectionRow } from "@/lib/data-onboarding/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { OnboardingEmptyState } from "./OnboardingEmptyState";

type GapDetectionStepProps = {
  rows: GapDetectionRow[];
  healthRows: DataHealthRow[];
  loadState: string;
  onDetectGaps: () => void;
};

export function GapDetectionStep({ rows, healthRows, loadState, onDetectGaps }: GapDetectionStepProps) {
  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Step 4</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Gap detection</h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Create backend gap plans for the checked windows and display missing final-candle ranges.
          </p>
        </div>
        <button
          type="button"
          disabled={healthRows.length === 0 || loadState === "loading"}
          onClick={onDetectGaps}
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {loadState === "loading" ? "Detecting" : "Detect gaps"}
        </button>
      </div>
      {rows.length === 0 ? (
        <OnboardingEmptyState
          title="No gap detection run"
          message="Run freshness first, then detect gaps for the same symbol and timeframe windows."
        />
      ) : (
        <div className="grid gap-4">
          {rows.map((row) => (
            <div key={`${row.health.target.symbol.id}-${row.health.target.timeframe}`} className="rounded-lg border border-[var(--line)] p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">
                    {row.health.target.symbol.symbol} · {row.health.target.timeframe}
                  </p>
                  <p className="mt-1 text-sm text-slate-500">
                    {formatDateTime(row.health.target.startTime)} to {formatDateTime(row.health.target.endTime)}
                  </p>
                </div>
                <Badge value={row.plan ? row.plan.status : "Backend unavailable"} tone={toneForQuality(row.plan?.status)} />
              </div>
              {row.errors.length > 0 && <p className="mt-3 text-sm text-red-700 dark:text-red-200">{row.errors[0].message}</p>}
              {row.plan && (
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <Metric label="Detected gaps" value={String(row.plan.detected_gap_count)} />
                  <Metric label="Planned requests" value={String(row.plan.planned_request_count)} />
                  <Metric label="Summary" value={row.plan.summary || "No missing candles"} />
                </div>
              )}
              {row.items.length > 0 && (
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="text-xs uppercase text-slate-500">
                      <tr>
                        <th className="border-b border-[var(--line)] px-3 py-2">Gap range</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Expected candles</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Method</th>
                        <th className="border-b border-[var(--line)] px-3 py-2">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {row.items.map((item) => (
                        <tr key={item.id}>
                          <td className="border-b border-[var(--line)] px-3 py-3">
                            {formatDateTime(item.gap_start_time)} to {formatDateTime(item.gap_end_time)}
                          </td>
                          <td className="border-b border-[var(--line)] px-3 py-3">{item.expected_candle_count}</td>
                          <td className="border-b border-[var(--line)] px-3 py-3">{item.recovery_method}</td>
                          <td className="border-b border-[var(--line)] px-3 py-3">
                            <Badge value={item.status} tone={toneForQuality(item.status)} />
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

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="muted-surface rounded-lg p-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
