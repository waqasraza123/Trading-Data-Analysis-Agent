"use client";

import { FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import type { SetupWizardStepProps } from "@/lib/setup-wizard/types";

export function DataSourceStep({ initialData, selectedSourceId, mutation, onComplete, onLocalSelectionChange }: SetupWizardStepProps) {
  const [mode, setMode] = useState<"create" | "select">(initialData.dataSources.length ? "select" : "create");
  const [sourceId, setSourceId] = useState(selectedSourceId || initialData.dataSources[0]?.id || "");
  const [sourceType, setSourceType] = useState("mock");
  const [name, setName] = useState("setup_demo_source");
  const [provider, setProvider] = useState("mock");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input =
      mode === "select"
        ? { mode, data_source_id: sourceId }
        : { mode, source_type: sourceType, name, provider, config_json: { demo: sourceType === "mock", syntheticFixtures: sourceType === "mock" } };
    onLocalSelectionChange({ sourceId: mode === "select" ? sourceId : null });
    await onComplete("data_source", input);
  }

  return (
    <Panel title="Data source" eyebrow="Stored candle source">
      <form className="grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Mode
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={mode} onChange={(event) => setMode(event.target.value as "create" | "select")}>
            <option value="select">Select existing</option>
            <option value="create">Create new</option>
          </select>
        </label>
        {mode === "select" ? (
          <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
            Source
            <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={sourceId} onChange={(event) => setSourceId(event.target.value)}>
              {initialData.dataSources.map((source) => (
                <option key={source.id} value={source.id}>{source.name} · {source.provider}</option>
              ))}
            </select>
          </label>
        ) : (
          <>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Type
              <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={sourceType} onChange={(event) => setSourceType(event.target.value)}>
                <option value="mock">Mock / demo</option>
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="provider">Provider polling</option>
                <option value="live">Live feed</option>
              </select>
            </label>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Name
              <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} />
            </label>
            <label className="text-sm font-medium text-slate-600 dark:text-slate-300">
              Provider
              <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2" value={provider} onChange={(event) => setProvider(event.target.value)} />
            </label>
          </>
        )}
        <div className="md:col-span-2">
          <button className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={mutation.status === "pending"} type="submit">
            Save data source
          </button>
        </div>
      </form>
    </Panel>
  );
}
