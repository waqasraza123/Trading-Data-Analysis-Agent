"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import {
  archiveScannerScanConfig,
  pauseScannerScanConfig,
  resumeScannerScanConfig,
  runScannerDueScans,
  runScannerScanConfig,
} from "@/lib/api/scanner";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { scanTargetLabel, sourceLabel, statusTone } from "@/lib/scanner/labels";
import type { ScannerData } from "@/lib/scanner/types";

export function ScanConfigList({ data }: { data: ScannerData }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const watchlistNames = new Map(data.watchlists.map(({ watchlist }) => [watchlist.id, watchlist.name]));

  async function updateConfig(configId: string, action: "pause" | "resume" | "archive") {
    setPendingAction(`${action}-${configId}`);
    setMessage(null);
    const result =
      action === "pause"
        ? await pauseScannerScanConfig(configId)
        : action === "resume"
          ? await resumeScannerScanConfig(configId)
          : await archiveScannerScanConfig(configId);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  async function runConfig(configId: string) {
    setPendingAction(`run-${configId}`);
    setMessage(null);
    const result = await runScannerScanConfig(configId);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.push(scannerRunHref(searchParams.toString(), data.workspace?.id || null, result.data.id));
    router.refresh();
  }

  async function runDue() {
    setPendingAction("run-due");
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
    setMessage(`Completed ${result.data.run_count} due scan run${result.data.run_count === 1 ? "" : "s"}.`);
    if (firstRun) {
      router.push(scannerRunHref(searchParams.toString(), data.workspace?.id || null, firstRun.id));
    }
    router.refresh();
  }

  return (
    <Panel
      title="Scan configs"
      eyebrow="Schedules and manual runs"
      action={
        <button
          className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={pendingAction === "run-due" || data.dueScanConfigs.length === 0}
          type="button"
          onClick={runDue}
        >
          {pendingAction === "run-due" ? "Running due scans" : "Run due scans"}
        </button>
      }
    >
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      {data.scanConfigs.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">No scheduled scan configs returned.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2 pr-3 font-semibold">Config</th>
                <th className="py-2 pr-3 font-semibold">Target</th>
                <th className="py-2 pr-3 font-semibold">Cadence</th>
                <th className="py-2 pr-3 font-semibold">Options</th>
                <th className="py-2 pr-3 font-semibold">Status</th>
                <th className="py-2 pr-0 text-right font-semibold">Controls</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--line)]">
              {data.scanConfigs.map((config) => (
                <tr key={config.id}>
                  <td className="py-3 pr-3 align-top">
                    <p className="font-semibold text-[var(--strong)]">{config.name}</p>
                    <p className="mt-1 text-xs text-slate-500">Next {formatRelativeTime(config.next_run_at)}</p>
                    <p className="mt-1 text-xs text-slate-500">Last {formatDateTime(config.last_run_at)}</p>
                  </td>
                  <td className="py-3 pr-3 align-top">
                    <p>{scanTargetLabel(config, config.watchlist_id ? watchlistNames.get(config.watchlist_id) || null : null, data.symbols)}</p>
                    <p className="mt-1 text-xs text-slate-500">{sourceLabel(data.dataSources, config.source_id)}</p>
                  </td>
                  <td className="py-3 pr-3 align-top text-slate-500">
                    <p>{config.lookback_minutes} min lookback</p>
                    <p className="mt-1">{config.interval_seconds} sec interval</p>
                  </td>
                  <td className="py-3 pr-3 align-top">
                    <div className="flex flex-wrap gap-1.5">
                      {config.include_partial_live_candle && <Badge value="Partial candle" tone="info" />}
                      {config.include_news_correlation && <Badge value="News correlation" tone="info" />}
                      {config.include_ai_explanation && <Badge value="AI explanation" tone="info" />}
                      {config.include_reasoning && <Badge value="Reasoning" tone="info" />}
                      {config.include_action_plan && <Badge value="Action plan record" tone="info" />}
                      {!config.include_partial_live_candle && !config.include_news_correlation && !config.include_ai_explanation && !config.include_reasoning && !config.include_action_plan && <Badge value="Deterministic only" tone="neutral" />}
                    </div>
                  </td>
                  <td className="py-3 pr-3 align-top">
                    <Badge value={config.status} tone={statusTone(config.status)} />
                  </td>
                  <td className="py-3 pr-0 align-top">
                    <div className="flex flex-wrap justify-end gap-2">
                      <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:hover:bg-slate-800" disabled={pendingAction === `run-${config.id}` || config.status === "archived"} type="button" onClick={() => runConfig(config.id)}>
                        {pendingAction === `run-${config.id}` ? "Running" : "Run scan"}
                      </button>
                      {config.status === "active" && (
                        <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800" type="button" onClick={() => updateConfig(config.id, "pause")}>
                          Pause
                        </button>
                      )}
                      {config.status === "paused" && (
                        <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800" type="button" onClick={() => updateConfig(config.id, "resume")}>
                          Resume
                        </button>
                      )}
                      {config.status !== "archived" && (
                        <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800" type="button" onClick={() => updateConfig(config.id, "archive")}>
                          Archive
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
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
