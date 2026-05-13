"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { cancelEquityDataOperation } from "@/lib/api/equityData";
import { equityDataLabel, equityDataStatusTone, formatContextDate } from "@/lib/equity-data/labels";
import type { EquityDataImportError, EquityDataOperation } from "@/lib/equity-data/types";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityDataOperationsPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const searchParams = useSearchParams();
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
                <ButtonLink href={operationHref(searchParams, operation.id)} size="sm">
                  Details
                </ButtonLink>
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
      {data.selectedOperation && (
        <div className="mt-4 rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-[var(--strong)]">
                {equityDataLabel(data.selectedOperation.operation_type)} details
              </h3>
              <p className="mt-1 text-xs text-slate-500">
                {data.selectedOperation.id.slice(0, 8)} · {equityDataLabel(data.selectedOperation.status)} · {formatContextDate(data.selectedOperation.updated_at)}
              </p>
            </div>
            <ButtonLink href={operationHref(searchParams, null)} size="sm" variant="quiet">
              Close
            </ButtonLink>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <OperationSummaryCard label="Rows received" value={counter(data.selectedOperation, "rows_received")} />
            <OperationSummaryCard label="Rows processed" value={counter(data.selectedOperation, "rows_processed")} />
            <OperationSummaryCard label="Warnings" value={counter(data.selectedOperation, "warnings_count")} />
          </div>
          <div className="mt-4 grid gap-3 text-xs text-slate-500">
            <JsonSummary title="Request summary" value={data.selectedOperation.request_summary_json} />
            <JsonSummary title="Result summary" value={data.selectedOperation.result_summary_json} />
          </div>
          <div className="mt-4">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Recent row errors</h4>
            <div className="mt-2 grid gap-2">
              {data.selectedOperation.recent_errors.map((error) => (
                <OperationErrorRow key={error.id} error={error} />
              ))}
              {data.selectedOperation.recent_errors.length === 0 && (
                <p className="rounded-md bg-[var(--panel-muted)] px-3 py-2 text-xs text-slate-500">
                  No row-level import errors recorded for this operation.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}

function OperationSummaryCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-[var(--line)] bg-[var(--panel-muted)] px-3 py-2">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-base font-semibold text-[var(--strong)]">{value}</div>
    </div>
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

function OperationErrorRow({ error }: { error: EquityDataImportError }) {
  return (
    <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-900 dark:border-rose-900 dark:bg-rose-950 dark:text-rose-100">
      <div className="font-semibold">
        {error.row_number ? `Row ${error.row_number}` : "Operation row"} · {equityDataLabel(error.error_code)}
      </div>
      <div className="mt-1">{error.error_message}</div>
    </div>
  );
}

function JsonSummary({ title, value }: { title: string; value: Record<string, unknown> }) {
  const entries = Object.entries(value || {}).slice(0, 6);
  return (
    <div className="rounded-md border border-[var(--line)] bg-[var(--panel-muted)] px-3 py-2">
      <div className="font-semibold text-[var(--strong)]">{title}</div>
      {entries.length > 0 ? (
        <dl className="mt-2 grid gap-1">
          {entries.map(([key, nestedValue]) => (
            <div key={key} className="grid grid-cols-[120px_minmax(0,1fr)] gap-2">
              <dt className="truncate text-slate-500">{equityDataLabel(key)}</dt>
              <dd className="truncate text-[var(--strong)]">{formatSummaryValue(nestedValue)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="mt-2 text-slate-500">No summary fields recorded.</p>
      )}
    </div>
  );
}

function canCancelOperation(operation: EquityDataOperation): boolean {
  return operation.status === "pending" || operation.status === "running";
}

function operationHref(searchParams: URLSearchParams | ReadonlyURLSearchParamsLike, operationId: string | null): string {
  const params = new URLSearchParams(searchParams.toString());
  if (operationId) {
    params.set("operationId", operationId);
  } else {
    params.delete("operationId");
  }
  const query = params.toString();
  return query ? `/equity-research?${query}` : "/equity-research";
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

function formatSummaryValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "None";
  }
  if (Array.isArray(value)) {
    return `${value.length} items`;
  }
  if (typeof value === "object") {
    return "Object";
  }
  return String(value);
}

type ReadonlyURLSearchParamsLike = {
  toString: () => string;
};
