"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Badge } from "@/components/status/badge";
import { deactivateScannerWatchlistItem } from "@/lib/api/scanner";
import { compactSymbolLabel, sourceLabel } from "@/lib/scanner/labels";
import type { SymbolRead, WatchlistItem } from "@/lib/api/types";
import type { ScannerDataSource } from "@/lib/scanner/types";

type WatchlistItemTableProps = {
  items: WatchlistItem[];
  symbols: SymbolRead[];
  dataSources: ScannerDataSource[];
};

export function WatchlistItemTable({ items, symbols, dataSources }: WatchlistItemTableProps) {
  const router = useRouter();
  const [pendingItemId, setPendingItemId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function deactivateItem(itemId: string) {
    setPendingItemId(itemId);
    setError(null);
    const result = await deactivateScannerWatchlistItem(itemId);
    setPendingItemId(null);
    if (!result.ok) {
      setError(result.error.message);
      return;
    }
    router.refresh();
  }

  if (items.length === 0) {
    return (
      <div className="mt-4 rounded-md border border-dashed border-[var(--line)] p-4 text-sm text-slate-500">
        No active symbol/timeframe items.
      </div>
    );
  }

  return (
    <div className="mt-4 overflow-x-auto">
      {error && <p className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-100">{error}</p>}
      <table className="w-full min-w-[560px] text-left text-sm">
        <thead className="text-xs uppercase text-slate-500">
          <tr>
            <th className="py-2 pr-3 font-semibold">Symbol</th>
            <th className="py-2 pr-3 font-semibold">Timeframe</th>
            <th className="py-2 pr-3 font-semibold">Source</th>
            <th className="py-2 pr-3 font-semibold">Candle mode</th>
            <th className="py-2 pr-0 text-right font-semibold">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--line)]">
          {items.map((item) => (
            <tr key={item.id}>
              <td className="py-3 pr-3 font-medium text-[var(--strong)]">{compactSymbolLabel(symbols, item.symbol_id)}</td>
              <td className="py-3 pr-3">{item.timeframe}</td>
              <td className="py-3 pr-3 text-slate-500">{sourceLabel(dataSources, item.source_id)}</td>
              <td className="py-3 pr-3">
                <Badge value={item.include_partial_live_candle ? "Partial allowed" : "Final candles"} tone="info" />
              </td>
              <td className="py-3 pr-0 text-right">
                <button
                  type="button"
                  className="rounded-md border border-[var(--line)] px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:text-slate-200 dark:hover:bg-slate-800"
                  disabled={pendingItemId === item.id}
                  onClick={() => deactivateItem(item.id)}
                >
                  {pendingItemId === item.id ? "Removing" : "Remove"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
