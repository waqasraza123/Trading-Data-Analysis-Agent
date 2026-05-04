"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { applyScannerPreset, seedScannerPresets } from "@/lib/api/scanner";
import { compactSymbolLabel, scannerTimeframes } from "@/lib/scanner/labels";
import type { ScannerData, ScannerPreset } from "@/lib/scanner/types";

type ScannerPresetGalleryProps = {
  data: ScannerData;
};

export function ScannerPresetGallery({ data }: ScannerPresetGalleryProps) {
  const router = useRouter();
  const [selectedPreset, setSelectedPreset] = useState<ScannerPreset | null>(null);
  const [selectedSymbolIds, setSelectedSymbolIds] = useState<string[]>([]);
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [createWatchlist, setCreateWatchlist] = useState(true);
  const [createScanConfig, setCreateScanConfig] = useState(true);
  const [nameOverride, setNameOverride] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const presetsByCategory = useMemo(() => groupPresets(data.presets), [data.presets]);

  function openPreset(preset: ScannerPreset) {
    const templateSymbols = resolveTemplateSymbolIds(preset, data);
    const timeframes = preset.timeframe_templates_json.filter((item) =>
      scannerTimeframes.includes(item as (typeof scannerTimeframes)[number]),
    );
    setSelectedPreset(preset);
    setSelectedSymbolIds(templateSymbols);
    setSelectedTimeframes(timeframes.length > 0 ? timeframes : ["5m"]);
    setSourceId("");
    setCreateWatchlist(true);
    setCreateScanConfig(true);
    setNameOverride("");
    setMessage(null);
  }

  async function seedPresets() {
    setPendingAction("seed");
    setMessage(null);
    const result = await seedScannerPresets();
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage(`Seeded ${result.data.seeded_count} scanner presets.`);
    router.refresh();
  }

  async function applyPreset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace || !selectedPreset) {
      setMessage("Workspace and preset are required.");
      return;
    }
    if (selectedTimeframes.length === 0) {
      setMessage("Choose at least one timeframe.");
      return;
    }
    if (!createWatchlist && !createScanConfig) {
      setMessage("Choose a watchlist, scan config, or both.");
      return;
    }
    setPendingAction("apply");
    setMessage(null);
    const result = await applyScannerPreset(selectedPreset.id, {
      workspace_id: data.workspace.id,
      symbol_ids: selectedSymbolIds,
      source_id: sourceId || undefined,
      timeframes: selectedTimeframes,
      create_watchlist: createWatchlist,
      create_scan_config: createScanConfig,
      name_override: nameOverride || undefined,
    });
    setPendingAction(null);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const created = [
      result.data.watchlist_id ? "watchlist" : null,
      result.data.scan_config_id ? "scan config" : null,
    ].filter(Boolean);
    setMessage(`Applied preset. Created ${created.join(" and ") || "application record"}.`);
    setSelectedPreset(null);
    router.refresh();
  }

  return (
    <Panel
      title="Scanner presets"
      eyebrow="Watchlist and scan config templates"
      action={
        <button
          className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60 dark:hover:bg-slate-800"
          disabled={pendingAction === "seed"}
          type="button"
          onClick={seedPresets}
        >
          {pendingAction === "seed" ? "Seeding" : "Seed defaults"}
        </button>
      }
    >
      {message && (
        <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">
          {message}
        </p>
      )}
      {data.presets.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">
          No scanner presets returned. Seed defaults when the backend endpoint is available.
        </div>
      ) : (
        <div className="space-y-5">
          {presetsByCategory.map(({ category, presets }) => (
            <section key={category}>
              <div className="mb-3 flex items-center gap-2">
                <Badge value={categoryLabel(category)} tone="info" />
                <span className="text-xs text-slate-500">{presets.length} presets</span>
              </div>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {presets.map((preset) => (
                  <article key={preset.id} className="muted-surface rounded-lg p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-[var(--strong)]">{preset.name}</h3>
                        <p className="mt-2 text-sm leading-6 text-slate-500">
                          {preset.description}
                        </p>
                      </div>
                      <Badge value={preset.preset_version} tone="neutral" />
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {preset.market_types_json.map((marketType) => (
                        <Badge key={marketType} value={marketType} />
                      ))}
                      {preset.timeframe_templates_json.map((timeframe) => (
                        <Badge key={timeframe} value={timeframe} tone="info" />
                      ))}
                    </div>
                    <button
                      className="mt-4 rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={!data.workspace}
                      type="button"
                      onClick={() => openPreset(preset)}
                    >
                      Apply preset
                    </button>
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
      {selectedPreset && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/45 p-4">
          <form
            className="mt-10 w-full max-w-3xl rounded-lg border border-[var(--line)] bg-[var(--panel)] p-5 shadow-xl"
            onSubmit={applyPreset}
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500">Apply preset</p>
                <h3 className="mt-1 text-xl font-semibold text-[var(--strong)]">
                  {selectedPreset.name}
                </h3>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                  Creates selected watchlist and scan config records only. It does not run the scan.
                </p>
              </div>
              <button
                className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800"
                type="button"
                onClick={() => setSelectedPreset(null)}
              >
                Close
              </button>
            </div>
            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
                Name override
                <input
                  className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
                  maxLength={160}
                  placeholder={selectedPreset.name}
                  value={nameOverride}
                  onChange={(event) => setNameOverride(event.target.value)}
                />
              </label>
              <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
                Source
                <select
                  className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
                  value={sourceId}
                  onChange={(event) => setSourceId(event.target.value)}
                >
                  <option value="">Any active source</option>
                  {data.dataSources.map((source) => (
                    <option key={source.id} value={source.id}>
                      {source.name} · {source.provider}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <fieldset className="mt-5">
              <legend className="text-sm font-semibold text-[var(--strong)]">Symbols</legend>
              <div className="mt-3 grid max-h-56 gap-2 overflow-y-auto rounded-lg border border-[var(--line)] p-3 sm:grid-cols-2">
                {data.symbols.map((symbol) => (
                  <label key={symbol.id} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      checked={selectedSymbolIds.includes(symbol.id)}
                      type="checkbox"
                      onChange={(event) =>
                        setSelectedSymbolIds((current) =>
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
            </fieldset>
            <fieldset className="mt-5">
              <legend className="text-sm font-semibold text-[var(--strong)]">Timeframes</legend>
              <div className="mt-3 flex flex-wrap gap-3">
                {scannerTimeframes.map((timeframe) => (
                  <label key={timeframe} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
                    <input
                      checked={selectedTimeframes.includes(timeframe)}
                      type="checkbox"
                      onChange={(event) =>
                        setSelectedTimeframes((current) =>
                          event.target.checked
                            ? Array.from(new Set([...current, timeframe]))
                            : current.filter((item) => item !== timeframe),
                        )
                      }
                    />
                    {timeframe}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <label className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                <input
                  checked={createWatchlist}
                  type="checkbox"
                  onChange={(event) => setCreateWatchlist(event.target.checked)}
                />
                Create watchlist
              </label>
              <label className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
                <input
                  checked={createScanConfig}
                  type="checkbox"
                  onChange={(event) => setCreateScanConfig(event.target.checked)}
                />
                Create scan config
              </label>
            </div>
            <div className="mt-5 rounded-lg border border-[var(--line)] p-4 text-sm text-slate-600 dark:text-slate-300">
              <p className="font-semibold text-[var(--strong)]">Created on apply</p>
              <p className="mt-2">
                {createWatchlist ? "Watchlist" : "No watchlist"} ·{" "}
                {createScanConfig ? "Scheduled scan config" : "No scan config"} ·{" "}
                {selectedSymbolIds.length || "no"} symbols · {selectedTimeframes.join(", ")}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                Template symbols: {selectedSymbolIds.map((id) => compactSymbolLabel(data.symbols, id)).join(", ") || "none selected"}
              </p>
            </div>
            <div className="mt-5 flex flex-wrap justify-end gap-3">
              <button
                className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800"
                type="button"
                onClick={() => setSelectedPreset(null)}
              >
                Cancel
              </button>
              <button
                className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
                disabled={pendingAction === "apply"}
                type="submit"
              >
                {pendingAction === "apply" ? "Applying" : "Apply preset"}
              </button>
            </div>
          </form>
        </div>
      )}
    </Panel>
  );
}

function groupPresets(presets: ScannerPreset[]): { category: string; presets: ScannerPreset[] }[] {
  const groups = new Map<string, ScannerPreset[]>();
  presets.forEach((preset) => {
    const current = groups.get(preset.category) || [];
    current.push(preset);
    groups.set(preset.category, current);
  });
  return Array.from(groups.entries()).map(([category, groupedPresets]) => ({
    category,
    presets: groupedPresets,
  }));
}

function resolveTemplateSymbolIds(preset: ScannerPreset, data: ScannerData): string[] {
  const codes = preset.symbol_templates_json.flatMap((template) => {
    const symbols = template.symbols;
    if (Array.isArray(symbols)) {
      return symbols.map(String);
    }
    const symbol = template.symbol;
    return typeof symbol === "string" ? [symbol] : [];
  });
  const ids = codes.flatMap((code) => {
    const symbol = data.symbols.find((item) => item.symbol === code);
    return symbol ? [symbol.id] : [];
  });
  return Array.from(new Set(ids));
}

function categoryLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
