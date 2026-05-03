import { Badge } from "@/components/status/badge";
import type { DataSource } from "@/lib/data-onboarding/types";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { providerHealthStatusLabel, providerHealthTone } from "@/lib/provider-health/labels";
import type { ProviderHealthSnapshot } from "@/lib/provider-health/types";
import type { SymbolRead, UUID } from "@/lib/api/types";
import { DataReadinessBadge } from "./DataReadinessBadge";
import { ProviderHealthEmptyState } from "./ProviderHealthEmptyState";

type ProviderHealthTableProps = {
  snapshots: ProviderHealthSnapshot[];
  symbols: SymbolRead[];
  dataSources: DataSource[];
  preparingSnapshotId: UUID | null;
  onPrepareRecovery: (snapshot: ProviderHealthSnapshot) => void;
};

export function ProviderHealthTable({
  snapshots,
  symbols,
  dataSources,
  preparingSnapshotId,
  onPrepareRecovery,
}: ProviderHealthTableProps) {
  if (snapshots.length === 0) {
    return (
      <ProviderHealthEmptyState
        title="No provider health snapshots"
        message="Refresh provider health to build source and symbol freshness snapshots."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[1080px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-xs uppercase text-slate-500">
            <th className="border-b border-[var(--line)] px-3 py-2">Source</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Symbol</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Timeframe</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Status</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Latest final candle</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Missing</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Failures</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Readiness</th>
            <th className="border-b border-[var(--line)] px-3 py-2">Recovery</th>
          </tr>
        </thead>
        <tbody>
          {snapshots.map((snapshot) => (
            <tr key={snapshot.id} className="align-top">
              <td className="border-b border-[var(--line)] px-3 py-3">
                <p className="font-semibold text-[var(--strong)]">
                  {sourceName(dataSources, snapshot.source_id)}
                </p>
                <p className="mt-1 text-xs text-slate-500">{snapshot.provider}</p>
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                {symbolName(symbols, snapshot.symbol_id)}
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                {snapshot.timeframe || "Source"}
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                <Badge
                  value={providerHealthStatusLabel(snapshot.status)}
                  tone={providerHealthTone(snapshot.status)}
                />
                <p className="mt-2 text-xs leading-5 text-slate-500">{snapshot.summary}</p>
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                <p>{formatDateTime(snapshot.latest_final_candle_time)}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {formatRelativeTime(snapshot.latest_final_candle_time)}
                </p>
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                {snapshot.missing_candle_count}
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                <p>{snapshot.consecutive_failure_count}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {formatDateTime(snapshot.latest_failed_poll_at)}
                </p>
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                <DataReadinessBadge snapshot={snapshot} />
              </td>
              <td className="border-b border-[var(--line)] px-3 py-3">
                <button
                  type="button"
                  disabled={!snapshot.symbol_id || !snapshot.timeframe || preparingSnapshotId === snapshot.id}
                  onClick={() => onPrepareRecovery(snapshot)}
                  className="rounded-md border border-[var(--line)] px-3 py-2 text-xs font-semibold text-[var(--strong)] disabled:opacity-40"
                >
                  {preparingSnapshotId === snapshot.id ? "Preparing" : "Prepare recovery plan"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function symbolName(symbols: SymbolRead[], symbolId: UUID | null): string {
  if (!symbolId) {
    return "Source";
  }
  const symbol = symbols.find((candidate) => candidate.id === symbolId);
  return symbol?.symbol || symbolId.slice(0, 8);
}

function sourceName(dataSources: DataSource[], sourceId: UUID): string {
  const source = dataSources.find((candidate) => candidate.id === sourceId);
  return source?.name || sourceId.slice(0, 8);
}
