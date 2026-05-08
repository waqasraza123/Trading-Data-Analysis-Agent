"use client";

import { FormEvent, useState } from "react";
import { cn } from "@/lib/ui/cn";
import { Panel } from "@/components/layout/panel";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function FirstScanStep({ initialData, selectedScanConfigId, mutation, onComplete, onSkip }: SetupWizardStepProps) {
  const [runScan, setRunScan] = useState(false);
  const [scanConfigId, setScanConfigId] = useState(selectedScanConfigId || initialData.scanConfigs[0]?.id || "");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!runScan) {
      await onSkip("first_scan");
      return;
    }
    await onComplete("first_scan", { run: true, scan_config_id: scanConfigId || undefined });
  }

  return (
    <AnimatedListItem
      as="section"
      className={cn(motionCardClass, motionRevealPresetClass("scale-subtle"))}
      style={motionRevealDensityStyle(0, "regular")}
    >
      <Panel title="First scan" eyebrow="Optional explicit run">
        <form className="space-y-4" onSubmit={submit}>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
            <input checked={runScan} type="checkbox" onChange={(event) => setRunScan(event.target.checked)} />
            Run the first deterministic scan now
          </label>
          {runScan && (
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
              Scan config
              <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={scanConfigId} onChange={(event) => setScanConfigId(event.target.value)}>
                {initialData.scanConfigs.map((config) => (
                  <option key={config.id} value={config.id}>{config.name}</option>
                ))}
              </select>
            </label>
          )}
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            {runScan ? "Run first scan" : "Finish without scan"}
          </button>
        </form>
      </Panel>
    </AnimatedListItem>
  );
}
