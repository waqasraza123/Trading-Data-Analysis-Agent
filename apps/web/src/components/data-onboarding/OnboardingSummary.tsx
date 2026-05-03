import { MetricCard } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import { summarizeDataHealth } from "@/lib/data-onboarding/composeDataHealth";
import type {
  DataHealthRow,
  GapDetectionRow,
  RecoveryPreparationRow,
} from "@/lib/data-onboarding/types";
import { OnboardingEmptyState } from "./OnboardingEmptyState";

type OnboardingSummaryProps = {
  healthRows: DataHealthRow[];
  gapRows: GapDetectionRow[];
  recoveryRows: RecoveryPreparationRow[];
  nextBackendActions: string[];
};

export function OnboardingSummary({
  healthRows,
  gapRows,
  recoveryRows,
  nextBackendActions,
}: OnboardingSummaryProps) {
  const summary = summarizeDataHealth(healthRows);
  const missingCandles = healthRows.reduce(
    (count, row) => count + (row.candleQuality?.missing_candles || 0),
    0,
  );
  const preparedRequests = recoveryRows.reduce(
    (count, row) => count + (row.preparation?.prepared_request_count || 0),
    0,
  );

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Step 6</p>
        <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Summary</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Readiness summary for deterministic analysis data inputs.
        </p>
      </div>
      {healthRows.length === 0 ? (
        <OnboardingEmptyState
          title="No checks completed"
          message="Complete freshness and gap checks to summarize readiness."
        />
      ) : (
        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Ready symbols" value={String(summary.ready)} detail="Ready for deterministic analysis" />
            <MetricCard label="Degraded" value={String(summary.degraded)} detail="Quality review needed" />
            <MetricCard label="Missing data" value={String(summary.missingData)} detail="Latest candle unavailable" />
            <MetricCard label="Stale feeds" value={String(summary.staleLiveFeeds)} detail="Live feed stale" />
            <MetricCard label="Missing candles" value={String(missingCandles)} detail="Across checked windows" />
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="rounded-lg border border-[var(--line)] p-4">
              <h4 className="text-sm font-semibold text-[var(--strong)]">Per-symbol status</h4>
              <div className="mt-3 grid gap-2">
                {healthRows.map((row) => (
                  <div key={`${row.target.symbol.id}-${row.target.timeframe}`} className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-[var(--panel-muted)] px-3 py-2 text-sm">
                    <span className="font-medium text-[var(--strong)]">
                      {row.target.symbol.symbol} · {row.target.timeframe}
                    </span>
                    <Badge value={row.statusLabel} tone={toneForQuality(row.status)} />
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-lg border border-[var(--line)] p-4">
              <h4 className="text-sm font-semibold text-[var(--strong)]">Next backend actions</h4>
              <div className="mt-3 grid gap-2 text-sm text-slate-600 dark:text-slate-300">
                {nextBackendActions.map((action) => (
                  <p key={action} className="rounded-md bg-[var(--panel-muted)] px-3 py-2">
                    {action}
                  </p>
                ))}
              </div>
              <div className="mt-4 grid gap-2 text-sm text-slate-500">
                <p>Gap plans: {gapRows.filter((row) => row.plan).length}</p>
                <p>Prepared provider polling requests: {preparedRequests}</p>
                <p>No broker execution or financial advice is part of this workflow.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
