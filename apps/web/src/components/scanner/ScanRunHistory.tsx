import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { statusTone } from "@/lib/scanner/labels";
import type { ScannerData } from "@/lib/scanner/types";

export function ScanRunHistory({ data }: { data: ScannerData }) {
  return (
    <Panel title="Scan run history" eyebrow="Recent completed work">
      {data.recentRuns.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm leading-6 text-slate-500">
          The backend exposes individual scan run lookup but not a recent scan run list. Run a config from this page to open the returned scan run detail.
        </div>
      ) : (
        <div className="grid gap-3">
          {data.recentRuns.map((run) => (
            <Link
              key={run.id}
              className="muted-surface rounded-lg p-4 hover:border-slate-400"
              href={`/scanner?workspaceId=${run.workspace_id}&runId=${run.id}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--strong)]">Scan run {run.id.slice(0, 8)}</p>
                  <p className="mt-1 text-xs text-slate-500">Completed {formatDateTime(run.completed_at)}</p>
                </div>
                <Badge value={run.status} tone={statusTone(run.status)} />
              </div>
              <div className="mt-4 grid gap-3 text-sm sm:grid-cols-4">
                <RunMetric label="Scanned" value={run.scanned_item_count} />
                <RunMetric label="Analysis runs" value={run.analysis_run_count} />
                <RunMetric label="Skipped" value={run.skipped_count} />
                <RunMetric label="Failed" value={run.failed_count} />
              </div>
            </Link>
          ))}
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
