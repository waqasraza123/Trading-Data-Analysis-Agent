"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/status/badge";
import { runEquitySwingScan } from "@/lib/api/equityResearch";
import { equityLabel, equityScanProfiles, equityTimeframes } from "@/lib/equity-research/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function SwingScanForm({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [scanProfileKey, setScanProfileKey] = useState<(typeof equityScanProfiles)[number]>("continuation_momentum");
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>(["1d", "4h"]);
  const [minAverageVolume, setMinAverageVolume] = useState("500000");
  const [minSetupScore, setMinSetupScore] = useState("0.60");
  const [maxSymbols, setMaxSymbols] = useState("500");
  const [useExistingAnalysisOnly, setUseExistingAnalysisOnly] = useState(true);
  const [generateSetupContext, setGenerateSetupContext] = useState(false);
  const [scoreSignalPriority, setScoreSignalPriority] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function toggleTimeframe(timeframe: string) {
    setSelectedTimeframes((current) =>
      current.includes(timeframe)
        ? current.filter((candidate) => candidate !== timeframe)
        : [...current, timeframe],
    );
  }

  async function submitScan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    if (!data.selectedUniverse) {
      setMessage("Create or select an equity universe first.");
      return;
    }
    if (selectedTimeframes.length === 0) {
      setMessage("Select at least one timeframe.");
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await runEquitySwingScan({
      workspace_id: data.workspace.id,
      universe_id: data.selectedUniverse.id,
      scan_profile_key: scanProfileKey,
      timeframes: selectedTimeframes,
      filters: {
        min_average_volume: Number(minAverageVolume),
        min_setup_score: Number(minSetupScore),
        max_symbols: Number(maxSymbols),
      },
      options: {
        use_existing_analysis_only: useExistingAnalysisOnly,
        generate_setup_context: generateSetupContext,
        score_signal_priority: scoreSignalPriority,
      },
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    params.set("workspaceId", data.workspace.id);
    params.set("universeId", data.selectedUniverse.id);
    params.set("scanRunId", result.data.id);
    router.push(`/equity-research?${params.toString()}`);
    router.refresh();
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Deterministic swing scan
          </p>
          <h2 className="mt-1 text-xl font-semibold text-[var(--strong)]">
            Generate ranked research candidates
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            The backend scores stored candles and persisted context. It does not call broker
            execution, notify externally, or change final signal classifications.
          </p>
        </div>
        <Badge
          value={data.selectedUniverse ? data.selectedUniverse.name : "No universe selected"}
          tone={data.selectedUniverse ? "info" : "warning"}
        />
      </div>
      {message && (
        <p className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          {message}
        </p>
      )}
      <form className="mt-5 grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]" onSubmit={submitScan}>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-semibold text-[var(--strong)]">
              Scan profile
              <select
                className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
                value={scanProfileKey}
                onChange={(event) =>
                  setScanProfileKey(event.target.value as (typeof equityScanProfiles)[number])
                }
              >
                {equityScanProfiles.map((profile) => (
                  <option key={profile} value={profile}>
                    {equityLabel(profile)}
                  </option>
                ))}
              </select>
            </label>
            <div>
              <p className="text-sm font-semibold text-[var(--strong)]">Timeframes</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {equityTimeframes.map((timeframe) => (
                  <label
                    key={timeframe}
                    className="inline-flex items-center gap-2 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
                  >
                    <input
                      checked={selectedTimeframes.includes(timeframe)}
                      type="checkbox"
                      onChange={() => toggleTimeframe(timeframe)}
                    />
                    {timeframe}
                  </label>
                ))}
              </div>
            </div>
            <NumberField label="Minimum average volume" value={minAverageVolume} onChange={setMinAverageVolume} />
            <NumberField label="Minimum setup score" value={minSetupScore} onChange={setMinSetupScore} />
            <NumberField label="Maximum symbols" value={maxSymbols} onChange={setMaxSymbols} />
          </div>
        </div>
        <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
          <p className="text-sm font-semibold text-[var(--strong)]">Run options</p>
          <div className="mt-3 grid gap-3 text-sm text-slate-600 dark:text-slate-300">
            <ToggleField
              checked={useExistingAnalysisOnly}
              label="Use existing analysis only"
              onChange={setUseExistingAnalysisOnly}
            />
            <ToggleField
              checked={generateSetupContext}
              label="Generate setup context"
              onChange={setGenerateSetupContext}
            />
            <ToggleField
              checked={scoreSignalPriority}
              label="Score signal priority context"
              onChange={setScoreSignalPriority}
            />
          </div>
          <button
            className="mt-5 w-full rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            disabled={!data.workspace || !data.selectedUniverse || pending}
            type="submit"
          >
            {pending ? "Running scan" : "Run swing scan"}
          </button>
        </div>
      </form>
    </section>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-sm font-semibold text-[var(--strong)]">
      {label}
      <input
        className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
        inputMode="decimal"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function ToggleField({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between gap-3 rounded-md border border-[var(--line)] px-3 py-2">
      <span>{label}</span>
      <input checked={checked} type="checkbox" onChange={(event) => onChange(event.target.checked)} />
    </label>
  );
}
