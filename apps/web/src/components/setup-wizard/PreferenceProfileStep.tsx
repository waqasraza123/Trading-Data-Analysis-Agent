"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function PreferenceProfileStep({ selectedSymbolIds, selectedTimeframes, mutation, onComplete, onSkip }: SetupWizardStepProps) {
  const [name, setName] = useState("Default review preferences");
  const [requireFreshData, setRequireFreshData] = useState(true);
  const [requireQuality, setRequireQuality] = useState(true);
  const [requireTimeframeAgreement, setRequireTimeframeAgreement] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onComplete("preference_profile", {
      mode: "create",
      name,
      market_types: ["crypto"],
      symbol_ids: selectedSymbolIds,
      timeframes: selectedTimeframes.length ? selectedTimeframes : ["1m", "5m", "15m"],
      require_fresh_data: requireFreshData,
      require_acceptable_data_quality: requireQuality,
      require_timeframe_agreement: requireTimeframeAgreement,
      is_default: true,
    });
  }

  return (
    <Panel title="Preference profile" eyebrow="Review filters">
      <form className="space-y-4" onSubmit={submit}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Profile name
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} />
        </label>
        <div className="grid gap-2 text-sm font-medium text-slate-600 dark:text-slate-300">
          <label className="flex items-center gap-2"><input checked={requireFreshData} type="checkbox" onChange={(event) => setRequireFreshData(event.target.checked)} /> Require fresh data</label>
          <label className="flex items-center gap-2"><input checked={requireQuality} type="checkbox" onChange={(event) => setRequireQuality(event.target.checked)} /> Require acceptable data quality</label>
          <label className="flex items-center gap-2"><input checked={requireTimeframeAgreement} type="checkbox" onChange={(event) => setRequireTimeframeAgreement(event.target.checked)} /> Require timeframe agreement</label>
        </div>
        <div className="flex flex-wrap gap-3">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            Create profile
          </button>
          <button className="rounded-md border border-[var(--line)] px-4 py-2 text-sm font-semibold" type="button" onClick={() => onSkip("preference_profile")}>
            Skip profile
          </button>
        </div>
      </form>
    </Panel>
  );
}
