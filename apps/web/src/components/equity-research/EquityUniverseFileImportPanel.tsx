"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import { importEquityUniverseFile } from "@/lib/api/equityData";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityUniverseFileImportPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [createName, setCreateName] = useState(data.selectedUniverse ? "" : "CSV Research Universe");
  const [runMode, setRunMode] = useState<"auto" | "queued" | "sync">("auto");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    if (!file) {
      setMessage("Choose a CSV file first.");
      return;
    }
    setPending(true);
    const result = await importEquityUniverseFile({
      workspaceId: data.workspace.id,
      file,
      universeId: createName.trim() ? undefined : data.selectedUniverse?.id,
      createUniverseName: createName.trim() || undefined,
      runMode,
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const operationId = result.data.operation?.id.slice(0, 8);
    setMessage(
      result.data.run_mode === "queued"
        ? `Queued ${result.data.rows_valid} valid rows for background import${operationId ? ` (${operationId})` : ""}.`
        : `Processed ${result.data.rows_valid} valid rows from ${result.data.rows_received} CSV rows.`,
    );
    router.refresh();
  }

  return (
    <Panel title="CSV file import" eyebrow="Research universe upload">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <form className="grid gap-4" onSubmit={submit}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Create universe name
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={createName} maxLength={160} onChange={(event) => setCreateName(event.target.value)} placeholder={data.selectedUniverse?.name || "Optional"} />
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          CSV file
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Run mode
          <select className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={runMode} onChange={(event) => setRunMode(event.target.value as "auto" | "queued" | "sync")}>
            <option value="auto">Auto</option>
            <option value="queued">Queued</option>
            <option value="sync">Sync</option>
          </select>
        </label>
        <p className="text-xs text-slate-500">
          Accepted columns: ticker or symbol, name, exchange, sector, industry, currency, country, asset_type. Credential-shaped columns are redacted.
        </p>
        <button className="w-fit rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={pending || !data.workspace} type="submit">
          {pending ? "Importing" : "Import research universe"}
        </button>
      </form>
    </Panel>
  );
}
