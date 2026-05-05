"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";
import { setupTimeframes } from "@/lib/setup-wizard/validation";

export function WatchlistStep({ initialData, selectedSymbolIds, selectedTimeframes, selectedSourceId, mutation, onComplete, onLocalSelectionChange }: SetupWizardStepProps) {
  const [name, setName] = useState("Workspace market review");
  const [timeframes, setTimeframes] = useState<string[]>(selectedTimeframes.length ? selectedTimeframes : ["1m", "5m", "15m"]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onLocalSelectionChange({ timeframes });
    await onComplete("watchlist", {
      mode: "create",
      name,
      description: "Workspace setup watchlist for deterministic scans.",
      symbol_ids: selectedSymbolIds.length ? selectedSymbolIds : initialData.symbols.slice(0, 2).map((symbol) => symbol.id),
      source_id: selectedSourceId || undefined,
      timeframes,
    });
  }

  return (
    <Panel title="Watchlist" eyebrow="Symbols and timeframes">
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Watchlist name
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <fieldset>
          <legend className="text-sm font-semibold text-[var(--strong)]">Timeframes</legend>
          <div className="mt-3 flex flex-wrap gap-3">
            {setupTimeframes.map((timeframe) => (
              <label key={timeframe} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                <input checked={timeframes.includes(timeframe)} type="checkbox" onChange={(event) => setTimeframes((current) => event.target.checked ? Array.from(new Set([...current, timeframe])) : current.filter((item) => item !== timeframe))} />
                {timeframe}
              </label>
            ))}
          </div>
        </fieldset>
        <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
          Create watchlist
        </button>
      </form>
    </Panel>
  );
}
