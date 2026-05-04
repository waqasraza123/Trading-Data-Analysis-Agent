"use client";

import { useRouter } from "next/navigation";
import { FormEvent, ReactNode, useMemo, useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { createScannerWatchlist, createScannerWatchlistItem, updateScannerWatchlist } from "@/lib/api/scanner";
import { scannerTimeframes, statusTone } from "@/lib/scanner/labels";
import type { ScannerData } from "@/lib/scanner/types";
import { validateWatchlistCreate, validateWatchlistItemCreate } from "@/lib/scanner/validation";
import { WatchlistItemTable } from "./WatchlistItemTable";

type WatchlistManagerProps = {
  data: ScannerData;
};

export function WatchlistManager({ data }: WatchlistManagerProps) {
  const router = useRouter();
  const activeWatchlists = useMemo(
    () => data.watchlists.filter(({ watchlist }) => watchlist.status !== "archived"),
    [data.watchlists],
  );
  const firstWatchlistId = activeWatchlists[0]?.watchlist.id || "";
  const firstSymbolId = data.symbols[0]?.id || "";
  const [watchlistName, setWatchlistName] = useState("");
  const [watchlistDescription, setWatchlistDescription] = useState("");
  const [selectedWatchlistId, setSelectedWatchlistId] = useState(firstWatchlistId);
  const [symbolId, setSymbolId] = useState(firstSymbolId);
  const [sourceId, setSourceId] = useState("");
  const [timeframe, setTimeframe] = useState("5m");
  const [includePartial, setIncludePartial] = useState(false);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function submitWatchlist(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    const input = {
      workspace_id: data.workspace.id,
      name: watchlistName,
      description: watchlistDescription || undefined,
    };
    const validation = validateWatchlistCreate(input);
    if (!validation.valid) {
      setMessage(validation.errors.join(" "));
      return;
    }
    setPendingAction("create-watchlist");
    setMessage(null);
    const result = await createScannerWatchlist(input);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setWatchlistName("");
    setWatchlistDescription("");
    router.refresh();
  }

  async function submitItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = {
      symbol_id: symbolId,
      source_id: sourceId || undefined,
      timeframe,
      include_partial_live_candle: includePartial,
    };
    const validation = validateWatchlistItemCreate(input);
    if (!selectedWatchlistId) {
      validation.errors.push("Watchlist is required.");
    }
    if (!validation.valid || validation.errors.length > 0) {
      setMessage(validation.errors.join(" "));
      return;
    }
    setPendingAction("add-item");
    setMessage(null);
    const result = await createScannerWatchlistItem(selectedWatchlistId, input);
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  async function updateWatchlistStatus(watchlistId: string, status: "active" | "paused" | "archived") {
    setPendingAction(`${status}-${watchlistId}`);
    setMessage(null);
    const result = await updateScannerWatchlist(watchlistId, { status });
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    router.refresh();
  }

  return (
    <Panel title="Watchlist management" eyebrow="Symbols and timeframes">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <div className="grid gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
        <div className="space-y-4">
          <form className="muted-surface rounded-lg p-4" onSubmit={submitWatchlist}>
            <h3 className="text-sm font-semibold text-[var(--strong)]">Create watchlist</h3>
            <label className="mt-4 block text-sm font-medium text-slate-600 dark:text-slate-300">
              Name
              <input
                className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
                value={watchlistName}
                maxLength={160}
                onChange={(event) => setWatchlistName(event.target.value)}
              />
            </label>
            <label className="mt-3 block text-sm font-medium text-slate-600 dark:text-slate-300">
              Description
              <input
                className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
                value={watchlistDescription}
                maxLength={1000}
                onChange={(event) => setWatchlistDescription(event.target.value)}
              />
            </label>
            <button
              className="mt-4 w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={pendingAction === "create-watchlist"}
              type="submit"
            >
              {pendingAction === "create-watchlist" ? "Creating" : "Create watchlist"}
            </button>
          </form>

          <form className="muted-surface rounded-lg p-4" onSubmit={submitItem}>
            <h3 className="text-sm font-semibold text-[var(--strong)]">Add item</h3>
            <Select label="Watchlist" value={selectedWatchlistId} onChange={setSelectedWatchlistId}>
              {activeWatchlists.length === 0 && <option value="">Create a watchlist first</option>}
              {activeWatchlists.map(({ watchlist }) => (
                <option key={watchlist.id} value={watchlist.id}>{watchlist.name}</option>
              ))}
            </Select>
            <Select label="Symbol" value={symbolId} onChange={setSymbolId}>
              {data.symbols.map((symbol) => (
                <option key={symbol.id} value={symbol.id}>{symbol.symbol} · {symbol.display_name}</option>
              ))}
            </Select>
            <Select label="Source" value={sourceId} onChange={setSourceId}>
              <option value="">Any active source</option>
              {data.dataSources.map((source) => (
                <option key={source.id} value={source.id}>{source.name} · {source.provider}</option>
              ))}
            </Select>
            <Select label="Timeframe" value={timeframe} onChange={setTimeframe}>
              {scannerTimeframes.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </Select>
            <label className="mt-3 flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
              <input type="checkbox" checked={includePartial} onChange={(event) => setIncludePartial(event.target.checked)} />
              Include partial live candle
            </label>
            <button
              className="mt-4 w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={pendingAction === "add-item" || activeWatchlists.length === 0 || data.symbols.length === 0}
              type="submit"
            >
              {pendingAction === "add-item" ? "Adding" : "Add item"}
            </button>
          </form>
        </div>

        <div className="space-y-4">
          {data.watchlists.length === 0 ? (
            <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">No watchlists returned by the backend.</div>
          ) : (
            data.watchlists.map(({ watchlist, items }) => (
              <div key={watchlist.id} className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-[var(--strong)]">{watchlist.name}</h3>
                    {watchlist.description && <p className="mt-1 text-sm text-slate-500">{watchlist.description}</p>}
                  </div>
                  <Badge value={watchlist.status} tone={statusTone(watchlist.status)} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {watchlist.status === "active" && (
                    <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800" disabled={pendingAction === `paused-${watchlist.id}`} type="button" onClick={() => updateWatchlistStatus(watchlist.id, "paused")}>
                      Pause
                    </button>
                  )}
                  {watchlist.status === "paused" && (
                    <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800" disabled={pendingAction === `active-${watchlist.id}`} type="button" onClick={() => updateWatchlistStatus(watchlist.id, "active")}>
                      Resume
                    </button>
                  )}
                  {watchlist.status !== "archived" && (
                    <button className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800" disabled={pendingAction === `archived-${watchlist.id}`} type="button" onClick={() => updateWatchlistStatus(watchlist.id, "archived")}>
                      Archive
                    </button>
                  )}
                </div>
                <WatchlistItemTable items={items} symbols={data.symbols} dataSources={data.dataSources} />
              </div>
            ))
          )}
        </div>
      </div>
    </Panel>
  );
}

function Select({
  label,
  value,
  children,
  onChange,
}: {
  label: string;
  value: string;
  children: ReactNode;
  onChange: (value: string) => void;
}) {
  return (
    <label className="mt-3 block text-sm font-medium text-slate-600 dark:text-slate-300">
      {label}
      <select
        className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {children}
      </select>
    </label>
  );
}
