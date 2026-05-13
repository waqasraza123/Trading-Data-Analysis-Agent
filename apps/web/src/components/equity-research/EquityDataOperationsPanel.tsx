"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { Button } from "@/components/ui/Button";
import { cancelEquityDataOperation } from "@/lib/api/equityData";
import { equityDataLabel, equityDataStatusTone, formatContextDate } from "@/lib/equity-data/labels";
import type { EquityDataOperation } from "@/lib/equity-data/types";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityDataOperationsPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const [pendingCancelId, setPendingCancelId] = useState<string | null>(null);
  const [rowMessage, setRowMessage] = useState<Record<string, string>>({});

  async function cancelOperation(operation: EquityDataOperation) {
    setPendingCancelId(operation.id);
    setRowMessage((current) => ({ ...current, [operation.id]: "" }));
    const result = await cancelEquityDataOperation(operation.id, {
      reason: "Stopped from the equity research operations panel",
    });
    if (!result.ok) {
      setRowMessage((current) => ({ ...current, [operation.id]: result.error.message }));
      setPendingCancelId(null);
      return;
    }
    setRowMessage((current) => ({ ...current, [operation.id]: "Operation stop requested." }));
    router.refresh();
    setPendingCancelId(null);
  }

  return (
    <Panel title="Background operations" eyebrow="Import and enrichment progress">
      <div className="mb-4 flex items-center justify-between gap-3">
        <p className="text-sm text-slate-500">
          Operations update research context and provider readiness. They do not place orders or provide financial advice.
        </p>
        <Button size="sm" type="button" onClick={() => router.refresh()}>
          Refresh
        </Button>
      </div>
      <div className="grid gap-3">
        {data.operations.map((operation) => (
          <div key={operation.id} className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--strong)]">{equityDataLabel(operation.operation_type)}</h3>
                <p className="mt-1 text-sm text-slate-500">
                  {operation.provider_name || "internal"} · {formatContextDate(operation.created_at)}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <Badge value={equityDataLabel(operation.status)} tone={equityDataStatusTone(operation.status)} />
                {canCancelOperation(operation) && (
                  <Button
                    size="sm"
                    variant="danger"
                    type="button"
                    loading={pendingCancelId === operation.id}
                    disabled={pendingCancelId !== null && pendingCancelId !== operation.id}
                    onClick={() => cancelOperation(operation)}
                  >
                    Stop
                  </Button>
                )}
              </div>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
              <div className="h-full bg-[var(--accent)]" style={{ width: `${progressPercent(operation.progress_current, operation.progress_total)}%` }} />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              {operation.progress_message || "Progress unavailable"} · {operation.progress_current}
              {operation.progress_total ? ` / ${operation.progress_total}` : ""}
            </p>
            <p className="mt-2 text-xs text-slate-500">
              Rows {counter(operation, "rows_processed")} · Snapshots {counter(operation, "snapshots_written")} · Events {counter(operation, "events_written")} · Catalysts {counter(operation, "catalysts_created")} · Errors {counter(operation, "errors_count")}
            </p>
            <dl className="mt-3 grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
              <OperationMeta label="Mode" value={operation.dry_run ? "Dry run" : "Persisting artifacts"} />
              <OperationMeta label="Job" value={shortId(operation.linked_job_id)} />
              <OperationMeta label="Provider request" value={shortId(operation.linked_provider_request_id)} />
            </dl>
            {rowMessage[operation.id] && (
              <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:bg-amber-950 dark:text-amber-100">
                {rowMessage[operation.id]}
              </p>
            )}
            {Object.keys(operation.error_summary_json || {}).length > 0 && (
              <p className="mt-2 rounded-md bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:bg-rose-950 dark:text-rose-100">
                {operation.status === "cancelled"
                  ? String(operation.error_summary_json.reason || "Operation was stopped")
                  : String(operation.error_summary_json.message || operation.error_summary_json.error_code || "Operation failed")}
              </p>
            )}
          </div>
        ))}
        {data.operations.length === 0 && (
          <p className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4 text-sm text-slate-500">
            No background equity data operations yet.
          </p>
        )}
      </div>
    </Panel>
  );
}

function OperationMeta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-semibold text-[var(--strong)]">{label}</dt>
      <dd className="mt-0.5">{value}</dd>
    </div>
  );
}

function canCancelOperation(operation: EquityDataOperation): boolean {
  return operation.status === "pending" || operation.status === "running";
}

function shortId(value: string | null): string {
  return value ? value.slice(0, 8) : "None";
}

function progressPercent(current: number, total: number | null): number {
  if (!total || total <= 0) {
    return current > 0 ? 100 : 0;
  }
  return Math.max(0, Math.min(100, Math.round((current / total) * 100)));
}

function counter(operation: { counters_json: Record<string, unknown> }, key: string): number {
  const value = operation.counters_json[key];
  return typeof value === "number" ? value : Number(value || 0);
}
