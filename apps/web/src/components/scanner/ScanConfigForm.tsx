"use client";

import { useRouter } from "next/navigation";
import { FormEvent, ReactNode, useState } from "react";
import { Panel } from "@/components/layout/panel";
import { createScannerScanConfig } from "@/lib/api/scanner";
import { scannerTimeframes } from "@/lib/scanner/labels";
import type { ScannerData, ScheduledScanConfigCreateInput } from "@/lib/scanner/types";
import { validateScanConfigCreate } from "@/lib/scanner/validation";

export function ScanConfigForm({ data }: { data: ScannerData }) {
  const router = useRouter();
  const activeWatchlists = data.watchlists.filter(({ watchlist }) => watchlist.status !== "archived");
  const [scanMode, setScanMode] = useState<"watchlist" | "single_symbol">("watchlist");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [watchlistId, setWatchlistId] = useState(activeWatchlists[0]?.watchlist.id || "");
  const [symbolId, setSymbolId] = useState(data.symbols[0]?.id || "");
  const [sourceId, setSourceId] = useState("");
  const [timeframe, setTimeframe] = useState("5m");
  const [lookbackMinutes, setLookbackMinutes] = useState(240);
  const [intervalSeconds, setIntervalSeconds] = useState(900);
  const [includePartial, setIncludePartial] = useState(false);
  const [includeNewsCorrelation, setIncludeNewsCorrelation] = useState(false);
  const [includeAiExplanation, setIncludeAiExplanation] = useState(false);
  const [includeReasoning, setIncludeReasoning] = useState(false);
  const [includeActionPlan, setIncludeActionPlan] = useState(false);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submitConfig(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    const input: ScheduledScanConfigCreateInput = {
      workspace_id: data.workspace.id,
      name,
      description: description || undefined,
      scan_mode: scanMode,
      watchlist_id: scanMode === "watchlist" ? watchlistId : undefined,
      symbol_id: scanMode === "single_symbol" ? symbolId : undefined,
      source_id: sourceId || undefined,
      timeframe: scanMode === "single_symbol" ? timeframe : undefined,
      lookback_minutes: Number(lookbackMinutes),
      interval_seconds: Number(intervalSeconds),
      include_partial_live_candle: includePartial,
      include_news_correlation: includeNewsCorrelation,
      include_ai_explanation: includeAiExplanation,
      include_reasoning: includeReasoning,
      include_action_plan: includeActionPlan,
    };
    const validation = validateScanConfigCreate(input);
    if (!validation.valid) {
      setMessage(validation.errors.join(" "));
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await createScannerScanConfig(input);
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setName("");
    setDescription("");
    router.refresh();
  }

  return (
    <Panel title="Create scan config" eyebrow="Scheduled deterministic analysis">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <form className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4" onSubmit={submitConfig}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Name
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} />
        </label>
        <Select label="Mode" value={scanMode} onChange={(value) => setScanMode(value as "watchlist" | "single_symbol")}>
          <option value="watchlist">Watchlist scan</option>
          <option value="single_symbol">Single-symbol scan</option>
        </Select>
        {scanMode === "watchlist" ? (
          <Select label="Watchlist" value={watchlistId} onChange={setWatchlistId}>
            {activeWatchlists.length === 0 && <option value="">Create a watchlist first</option>}
            {activeWatchlists.map(({ watchlist }) => (
              <option key={watchlist.id} value={watchlist.id}>{watchlist.name}</option>
            ))}
          </Select>
        ) : (
          <>
            <Select label="Symbol" value={symbolId} onChange={setSymbolId}>
              {data.symbols.map((symbol) => (
                <option key={symbol.id} value={symbol.id}>{symbol.symbol} · {symbol.display_name}</option>
              ))}
            </Select>
            <Select label="Timeframe" value={timeframe} onChange={setTimeframe}>
              {scannerTimeframes.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </Select>
          </>
        )}
        <Select label="Source" value={sourceId} onChange={setSourceId}>
          <option value="">Any active source</option>
          {data.dataSources.map((source) => (
            <option key={source.id} value={source.id}>{source.name} · {source.provider}</option>
          ))}
        </Select>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Lookback minutes
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" min={1} type="number" value={lookbackMinutes} onChange={(event) => setLookbackMinutes(Number(event.target.value))} />
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Interval seconds
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" min={1} type="number" value={intervalSeconds} onChange={(event) => setIntervalSeconds(Number(event.target.value))} />
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 lg:col-span-2">
          Description
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={description} maxLength={1000} onChange={(event) => setDescription(event.target.value)} />
        </label>
        <div className="grid gap-2 text-sm font-medium text-slate-600 dark:text-slate-300 lg:col-span-2 xl:col-span-4">
          <label className="flex items-center gap-2"><input type="checkbox" checked={includePartial} onChange={(event) => setIncludePartial(event.target.checked)} /> Include partial live candle</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={includeNewsCorrelation} onChange={(event) => setIncludeNewsCorrelation(event.target.checked)} /> Include news correlation</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={includeAiExplanation} onChange={(event) => setIncludeAiExplanation(event.target.checked)} /> Include AI explanation</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={includeReasoning} onChange={(event) => setIncludeReasoning(event.target.checked)} /> Include reasoning</label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={includeActionPlan} onChange={(event) => setIncludeActionPlan(event.target.checked)} /> Include action plan record</label>
        </div>
        <div className="lg:col-span-2 xl:col-span-4">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={pending || !data.workspace} type="submit">
            {pending ? "Creating config" : "Create scan config"}
          </button>
        </div>
      </form>
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
    <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
      {label}
      <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={value} onChange={(event) => onChange(event.target.value)}>
        {children}
      </select>
    </label>
  );
}
