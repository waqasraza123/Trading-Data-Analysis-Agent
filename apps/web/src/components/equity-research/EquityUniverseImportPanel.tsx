"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import { importEquityUniverseProvider, importEquityUniverseRows } from "@/lib/api/equityData";
import type { EquityResearchData } from "@/lib/equity-research/types";

const sampleRows = "AAPL,Apple Inc.,NASDAQ,Technology,Consumer Electronics,52000000\nMSFT,Microsoft Corporation,NASDAQ,Technology,Software Infrastructure,24500000";

export function EquityUniverseImportPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const [text, setText] = useState(sampleRows);
  const [createName, setCreateName] = useState(data.selectedUniverse ? "" : "Demo Equity Universe");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submitRows(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    const rows = parseRows(text);
    if (rows.length === 0) {
      setMessage("At least one ticker row is required.");
      return;
    }
    setPending(true);
    const result = await importEquityUniverseRows({
      workspaceId: data.workspace.id,
      universeId: createName.trim() ? undefined : data.selectedUniverse?.id,
      createUniverseName: createName.trim() || undefined,
      rows,
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage(`Stored ${result.data.stored_count} symbol rows; skipped ${result.data.skipped_count}.`);
    router.refresh();
  }

  async function importMock() {
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    setPending(true);
    const result = await importEquityUniverseProvider({
      workspaceId: data.workspace.id,
      provider: "mock_equity_data",
      universeId: createName.trim() ? undefined : data.selectedUniverse?.id,
      createUniverseName: createName.trim() || undefined,
      filters: { limit: 100 },
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage(`Stored ${result.data.stored_count} provider rows; skipped ${result.data.skipped_count}.`);
    router.refresh();
  }

  return (
    <Panel title="Universe import" eyebrow="Bulk symbol setup">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <form className="grid gap-4" onSubmit={submitRows}>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          Create universe name
          <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={createName} maxLength={160} onChange={(event) => setCreateName(event.target.value)} placeholder={data.selectedUniverse?.name || "Optional"} />
        </label>
        <label className="block text-sm font-medium text-slate-600 dark:text-slate-300">
          CSV rows
          <textarea className="mt-1 min-h-32 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 font-mono text-xs" value={text} onChange={(event) => setText(event.target.value)} />
        </label>
        <div className="flex flex-wrap gap-2">
          <button className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={pending || !data.workspace} type="submit">
            {pending ? "Importing" : "Import rows"}
          </button>
          <button className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold text-[var(--strong)] disabled:opacity-60" disabled={pending || !data.workspace} type="button" onClick={importMock}>
            Import mock universe
          </button>
        </div>
      </form>
    </Panel>
  );
}

function parseRows(text: string) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [ticker, companyName, exchange, sector, industry, averageVolume] = line.split(",").map((value) => value.trim());
      return { ticker, companyName, exchange, sector, industry, averageVolume };
    })
    .filter((row) => row.ticker);
}
