import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { compactSymbolLabel, sourceLabel, statusTone, safeScannerText } from "@/lib/scanner/labels";
import type { ScannerData } from "@/lib/scanner/types";

export function ScanRunDetail({ data }: { data: ScannerData }) {
  const run = data.selectedRun;

  return (
    <Panel title="Scan run detail" eyebrow="Items and deterministic outputs">
      {!run ? (
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">
          Select a returned scan run to inspect symbol/timeframe items, analysis run links, signal links, skipped reasons, and error messages.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-[var(--strong)]">Scan run {run.id.slice(0, 8)}</h3>
                <p className="mt-1 text-sm text-slate-500">Started {formatDateTime(run.started_at)} · Completed {formatDateTime(run.completed_at)}</p>
              </div>
              <Badge value={run.status} tone={statusTone(run.status)} />
            </div>
            {run.error_message && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-100">{safeScannerText(run.error_message)}</p>}
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-4">
              <RunMetric label="Scanned items" value={run.scanned_item_count} />
              <RunMetric label="Analysis runs" value={run.analysis_run_count} />
              <RunMetric label="Skipped" value={run.skipped_count} />
              <RunMetric label="Failed" value={run.failed_count} />
            </div>
          </div>
          {data.selectedRunItems.length === 0 ? (
            <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">No scan run items returned.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2 pr-3 font-semibold">Symbol</th>
                    <th className="py-2 pr-3 font-semibold">Timeframe</th>
                    <th className="py-2 pr-3 font-semibold">Source</th>
                    <th className="py-2 pr-3 font-semibold">Status</th>
                    <th className="py-2 pr-3 font-semibold">Analysis run</th>
                    <th className="py-2 pr-3 font-semibold">Signal</th>
                    <th className="py-2 pr-0 font-semibold">Notes</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)]">
                  {data.selectedRunItems.map((item) => (
                    <tr key={item.id}>
                      <td className="py-3 pr-3 font-medium text-[var(--strong)]">{compactSymbolLabel(data.symbols, item.symbol_id)}</td>
                      <td className="py-3 pr-3">{item.timeframe}</td>
                      <td className="py-3 pr-3 text-slate-500">{sourceLabel(data.dataSources, item.source_id)}</td>
                      <td className="py-3 pr-3"><Badge value={item.status} tone={statusTone(item.status)} /></td>
                      <td className="py-3 pr-3">
                        {item.analysis_run_id ? (
                          <Link className="font-mono text-xs text-[var(--info)]" href={`/symbols/${item.symbol_id}?workspaceId=${item.workspace_id}`}>
                            {item.analysis_run_id.slice(0, 8)}
                          </Link>
                        ) : (
                          <span className="text-slate-500">Not available</span>
                        )}
                      </td>
                      <td className="py-3 pr-3">
                        {item.signal_id ? <Link className="font-medium text-[var(--info)]" href={`/signals/${item.signal_id}`}>Review result</Link> : <span className="text-slate-500">No result</span>}
                      </td>
                      <td className="py-3 pr-0 text-slate-500">{safeScannerText(item.skipped_reason || item.error_message, "No note")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

function RunMetric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
