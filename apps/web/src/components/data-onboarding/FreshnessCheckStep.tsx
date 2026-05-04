import { Badge, toneForQuality } from "@/components/status/badge";
import type { DataHealthRow, DataSource } from "@/lib/data-onboarding/types";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { OnboardingEmptyState } from "./OnboardingEmptyState";

type FreshnessCheckStepProps = {
  rows: DataHealthRow[];
  validation: string[];
  loadState: string;
  selectedSource: DataSource | null;
  canRun: boolean;
  onRunFreshnessCheck: () => void;
};

export function FreshnessCheckStep({
  rows,
  validation,
  loadState,
  selectedSource,
  canRun,
  onRunFreshnessCheck,
}: FreshnessCheckStepProps) {
  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Step 3</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">Freshness check</h3>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            Check latest final candle, recent candle count, data quality, market memory, live feed, and polling state.
          </p>
        </div>
        <button
          type="button"
          disabled={!canRun || loadState === "loading"}
          onClick={onRunFreshnessCheck}
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40"
        >
          {loadState === "loading" ? "Checking" : "Run freshness check"}
        </button>
      </div>
      {validation.length > 0 && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          {validation.join(". ")}.
        </div>
      )}
      {selectedSource && (
        <div className="mb-4 rounded-lg border border-[var(--line)] p-3 text-sm text-slate-500">
          Source: <span className="font-semibold text-[var(--strong)]">{selectedSource.name}</span>
        </div>
      )}
      {rows.length === 0 ? (
        <OnboardingEmptyState
          title="Freshness not checked"
          message="Run the freshness check after selecting a source, symbols, and timeframes."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-xs uppercase text-slate-500">
                <th className="border-b border-[var(--line)] px-3 py-2">Symbol</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Timeframe</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Status</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Latest final candle</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Recent count</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Quality</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Memory</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Live</th>
                <th className="border-b border-[var(--line)] px-3 py-2">Polling</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.target.symbol.id}-${row.target.timeframe}`} className="align-top">
                  <td className="border-b border-[var(--line)] px-3 py-3 font-semibold text-[var(--strong)]">
                    {row.target.symbol.symbol}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">{row.target.timeframe}</td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    <Badge value={row.statusLabel} tone={toneForQuality(row.status)} />
                    {row.issues.length > 0 && (
                      <p className="mt-2 text-xs leading-5 text-slate-500">{row.issues.join(", ")}</p>
                    )}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    <p>{formatDateTime(row.latestFinalCandle?.timestamp)}</p>
                    <p className="mt-1 text-xs text-slate-500">{formatRelativeTime(row.latestFinalCandle?.timestamp)}</p>
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    {row.candleCount?.count ?? "Not available"}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    <p>{row.candleQuality?.quality_score ?? "Not available"}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Missing {row.candleQuality?.missing_candles ?? "not available"}
                    </p>
                    {row.dataQualityRun && (
                      <p className="mt-1 text-xs text-slate-500">Run label {row.dataQualityRun.quality_label}</p>
                    )}
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    <Badge value={row.marketMemory?.freshness_label || "Not available"} tone={toneForQuality(row.marketMemory?.freshness_label)} />
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    <Badge value={row.liveSubscription?.status || "Not available"} tone={toneForQuality(row.liveSubscription?.status)} />
                  </td>
                  <td className="border-b border-[var(--line)] px-3 py-3">
                    <Badge value={row.providerPollingRequest?.status || "Not available"} tone={toneForQuality(row.providerPollingRequest?.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
