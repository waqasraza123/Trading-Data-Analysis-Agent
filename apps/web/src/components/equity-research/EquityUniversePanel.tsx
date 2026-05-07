"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { createEquityUniverse } from "@/lib/api/equityResearch";
import { equityStatusTone } from "@/lib/equity-research/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

export function EquityUniversePanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submitUniverse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    if (!name.trim()) {
      setMessage("Universe name is required.");
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await createEquityUniverse({
      workspace_id: data.workspace.id,
      name,
      description: description || undefined,
      universe_type: "manual",
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setName("");
    setDescription("");
    router.push(`/equity-research?workspaceId=${data.workspace.id}&universeId=${result.data.id}`);
    router.refresh();
  }

  return (
    <Panel title="Equity universes" eyebrow="Stock research scope">
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <form className="muted-surface rounded-lg p-4" onSubmit={submitUniverse}>
          <h3 className="text-sm font-semibold text-[var(--strong)]">Create manual universe</h3>
          <label className="mt-4 block text-sm font-medium text-slate-600 dark:text-slate-300">
            Name
            <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={name} maxLength={160} onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="mt-3 block text-sm font-medium text-slate-600 dark:text-slate-300">
            Description
            <input className="mt-1 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm" value={description} maxLength={1000} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button className="mt-4 w-full rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60" disabled={pending || !data.workspace} type="submit">
            {pending ? "Creating" : "Create universe"}
          </button>
        </form>
        <div className="space-y-3">
          {data.universes.length === 0 ? (
            <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">No equity universes are available yet.</div>
          ) : (
            data.universes.map((universe) => (
              <Link
                key={universe.id}
                className="muted-surface block rounded-lg p-4 transition hover:border-[var(--accent)]"
                href={`/equity-research?workspaceId=${universe.workspace_id}&universeId=${universe.id}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-[var(--strong)]">{universe.name}</h3>
                    <p className="mt-1 text-sm text-slate-500">{universe.description || "Manual stock universe"}</p>
                  </div>
                  <Badge value={universe.status} tone={equityStatusTone(universe.status)} />
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </Panel>
  );
}
