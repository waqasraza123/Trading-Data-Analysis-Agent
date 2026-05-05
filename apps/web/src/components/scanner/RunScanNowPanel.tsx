"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";
import { Badge } from "@/components/status/badge";
import { runScannerDueScans, runScannerScanConfig } from "@/lib/api/scanner";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { scanTargetLabel, statusTone } from "@/lib/scanner/labels";
import type { ScannerData } from "@/lib/scanner/types";

export function RunScanNowPanel({ data }: { data: ScannerData }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const activeConfigs = data.scanConfigs.filter((config) => config.status === "active");
  const defaultConfigId = data.dueScanConfigs[0]?.id || activeConfigs[0]?.id || "";
  const [selectedConfigId, setSelectedConfigId] = useState(defaultConfigId);
  const [pendingAction, setPendingAction] = useState<"config" | "due" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const watchlistNames = useMemo(
    () => new Map(data.watchlists.map(({ watchlist }) => [watchlist.id, watchlist.name])),
    [data.watchlists],
  );
  const selectedConfig = activeConfigs.find((config) => config.id === selectedConfigId) || null;

  async function runSelectedConfig() {
    if (!selectedConfig) {
      setMessage("Choose an active scan config first.");
      return;
    }
    setPendingAction("config");
    setMessage(null);
    const result = await runScannerScanConfig(selectedConfig.id);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.push(scannerRunHref(searchParams.toString(), data.workspace?.id || null, result.data.id));
    router.refresh();
  }

  async function runDueConfigs() {
    setPendingAction("due");
    setMessage(null);
    const result = await runScannerDueScans({
      workspace_id: data.workspace?.id,
      limit: 50,
    });
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const firstRun = result.data.runs[0] || null;
    setMessage(`Scan completed for ${result.data.run_count} due config${result.data.run_count === 1 ? "" : "s"}.`);
    if (firstRun) {
      router.push(scannerRunHref(searchParams.toString(), data.workspace?.id || null, firstRun.id));
    }
    router.refresh();
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Run scan now
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[var(--strong)]">
            Explicit deterministic backend scan
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Choose a config, confirm the target, and run stored-candle analysis. Running a scan does
            not call brokers, place orders, or send external messages.
          </p>
        </div>
        <Badge value={data.dueScanConfigs.length > 0 ? `${data.dueScanConfigs.length} due` : "No due configs"} tone={data.dueScanConfigs.length > 0 ? "info" : "neutral"} />
      </div>
      {message && (
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          {message}
        </p>
      )}
      <div className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
          <label className="block text-sm font-semibold text-[var(--strong)]">
            Scan config
            <select
              className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
              value={selectedConfigId}
              onChange={(event) => setSelectedConfigId(event.target.value)}
            >
              {activeConfigs.length === 0 && <option value="">Create an active config first</option>}
              {activeConfigs.map((config) => (
                <option key={config.id} value={config.id}>
                  {config.name}
                </option>
              ))}
            </select>
          </label>
          {selectedConfig ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Detail label="Target" value={scanTargetLabel(selectedConfig, selectedConfig.watchlist_id ? watchlistNames.get(selectedConfig.watchlist_id) || null : null, data.symbols)} />
              <Detail label="Lookback" value={`${selectedConfig.lookback_minutes} min`} />
              <Detail label="Interval" value={`${selectedConfig.interval_seconds} sec`} />
              <Detail label="Next run" value={formatRelativeTime(selectedConfig.next_run_at)} />
            </div>
          ) : (
            <div className="mt-4 rounded-md border border-dashed border-[var(--line)] p-4 text-sm text-slate-500">
              No active config is available for run-now execution.
            </div>
          )}
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
          <p className="text-sm font-semibold text-[var(--strong)]">Confirmation</p>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            The backend will create analysis run records from configured candle windows and return a
            scan run id for review.
          </p>
          <div className="mt-4 grid gap-2">
            <button
              type="button"
              disabled={!selectedConfig || pendingAction !== null}
              onClick={runSelectedConfig}
              className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {pendingAction === "config" ? "Running scan" : "Run selected scan"}
            </button>
            <button
              type="button"
              disabled={data.dueScanConfigs.length === 0 || pendingAction !== null}
              onClick={runDueConfigs}
              className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold text-[var(--strong)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {pendingAction === "due" ? "Running due scans" : "Run due scans"}
            </button>
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Last selected run: {formatDateTime(data.selectedRun?.completed_at || data.selectedRun?.started_at)}
          </p>
        </div>
      </div>
    </section>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}

function scannerRunHref(searchParams: string, workspaceId: string | null, runId: string): string {
  const params = new URLSearchParams(searchParams);
  if (workspaceId) {
    params.set("workspaceId", workspaceId);
  }
  params.set("runId", runId);
  return `/scanner?${params.toString()}`;
}
