"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function ScannerPresetStep({ initialData, selectedSymbolIds, selectedTimeframes, selectedSourceId, mutation, onComplete, onSkip, onLocalSelectionChange }: SetupWizardStepProps) {
  const [presetId, setPresetId] = useState(initialData.scannerPresets.find((preset) => preset.key === "crypto_24h")?.id || initialData.scannerPresets[0]?.id || "");
  const [createWatchlist, setCreateWatchlist] = useState(false);
  const [createScanConfig, setCreateScanConfig] = useState(true);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onComplete("scanner_preset", {
      preset_id: presetId,
      symbol_ids: selectedSymbolIds,
      source_id: selectedSourceId || undefined,
      timeframes: selectedTimeframes.length ? selectedTimeframes : ["1m", "5m", "15m"],
      create_watchlist: createWatchlist,
      create_scan_config: createScanConfig,
      name_override: "Workspace setup scan",
    });
    onLocalSelectionChange({});
  }

  return (
    <Panel title="Scanner preset" eyebrow="Optional template">
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Preset
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={presetId} onChange={(event) => setPresetId(event.target.value)}>
            {initialData.scannerPresets.map((preset) => (
              <option key={preset.id} value={preset.id}>{preset.name} · {preset.preset_version}</option>
            ))}
          </select>
        </label>
        <div className="grid gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
          <label className="flex items-center gap-2"><input checked={createWatchlist} type="checkbox" onChange={(event) => setCreateWatchlist(event.target.checked)} /> Create preset watchlist</label>
          <label className="flex items-center gap-2"><input checked={createScanConfig} type="checkbox" onChange={(event) => setCreateScanConfig(event.target.checked)} /> Create scan config</label>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending" || !presetId} type="submit">
            Apply preset
          </button>
          <button className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold" type="button" onClick={() => onSkip("scanner_preset")}>
            Skip preset
          </button>
        </div>
      </form>
    </Panel>
  );
}
