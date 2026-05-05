"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";
import { normalizeSymbolCodes } from "@/lib/setup-wizard/validation";

export function SymbolsStep({ initialData, selectedSymbolIds, mutation, onComplete, onLocalSelectionChange }: SetupWizardStepProps) {
  const [marketType, setMarketType] = useState("crypto");
  const [symbolIds, setSymbolIds] = useState<string[]>(selectedSymbolIds.length ? selectedSymbolIds : initialData.symbols.filter((symbol) => symbol.market_type === "crypto").slice(0, 2).map((symbol) => symbol.id));
  const [symbolCodes, setSymbolCodes] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLocalSelectionChange({ symbolIds });
    await onComplete("symbols", {
      market_type: marketType,
      symbol_ids: symbolIds,
      symbol_codes: normalizeSymbolCodes(symbolCodes),
      create_missing_symbols: false,
    });
  }

  return (
    <Panel title="Symbols" eyebrow="Default market set">
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Market
          <select className="mt-1 w-full max-w-sm rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={marketType} onChange={(event) => setMarketType(event.target.value)}>
            <option value="crypto">Crypto</option>
            <option value="forex">Forex</option>
            <option value="commodity">Commodity</option>
            <option value="stock">Stock</option>
            <option value="index">Index</option>
          </select>
        </label>
        <div className="grid max-h-72 gap-2 overflow-y-auto rounded-lg border border-[var(--line)] p-3 sm:grid-cols-2 lg:grid-cols-3">
          {initialData.symbols.map((symbol) => (
            <label key={symbol.id} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
              <input
                checked={symbolIds.includes(symbol.id)}
                type="checkbox"
                onChange={(event) =>
                  setSymbolIds((current) =>
                    event.target.checked
                      ? Array.from(new Set([...current, symbol.id]))
                      : current.filter((item) => item !== symbol.id),
                  )
                }
              />
              {symbol.symbol} · {symbol.display_name}
            </label>
          ))}
        </div>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Additional existing symbol codes
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" placeholder="BTCUSDT, ETHUSDT" value={symbolCodes} onChange={(event) => setSymbolCodes(event.target.value)} />
        </label>
        <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
          Save symbols
        </button>
      </form>
    </Panel>
  );
}
