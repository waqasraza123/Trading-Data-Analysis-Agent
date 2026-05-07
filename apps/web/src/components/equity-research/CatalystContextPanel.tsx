"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { createEquityCatalyst } from "@/lib/api/equityResearch";
import { compactEquitySymbol, equityLabel, equityStatusTone } from "@/lib/equity-research/labels";
import type { EquityResearchData } from "@/lib/equity-research/types";

const catalystTypes = [
  "earnings",
  "guidance",
  "analyst_rating",
  "news",
  "sector_event",
  "macro_event",
  "unusual_volume",
  "manual_note",
];
const importanceValues = ["unknown", "low", "medium", "high"];
const sentimentValues = ["unknown", "bullish", "bearish", "neutral", "mixed"];

export function CatalystContextPanel({ data }: { data: EquityResearchData }) {
  const router = useRouter();
  const defaultSymbolId = data.selectedCandidate?.symbol_id || data.selectedUniverseMembers[0]?.symbol_id || "";
  const [symbolId, setSymbolId] = useState(defaultSymbolId);
  const [catalystType, setCatalystType] = useState("manual_note");
  const [importance, setImportance] = useState("unknown");
  const [sentiment, setSentiment] = useState("unknown");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submitCatalyst(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data.workspace) {
      setMessage("Workspace is required.");
      return;
    }
    if (!symbolId) {
      setMessage("Select a stock symbol.");
      return;
    }
    if (!title.trim() || !summary.trim()) {
      setMessage("Title and summary are required.");
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await createEquityCatalyst({
      workspace_id: data.workspace.id,
      symbol_id: symbolId,
      source_type: "manual",
      catalyst_type: catalystType,
      title,
      summary,
      importance,
      sentiment,
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setTitle("");
    setSummary("");
    router.refresh();
  }

  return (
    <Panel title="Catalyst context" eyebrow="Manual persisted context">
      {message && (
        <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">
          {message}
        </p>
      )}
      <form className="grid gap-3 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-4" onSubmit={submitCatalyst}>
        <label className="text-sm font-semibold text-[var(--strong)]">
          Symbol
          <select
            className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
            value={symbolId}
            onChange={(event) => setSymbolId(event.target.value)}
          >
            {data.selectedUniverseMembers.length === 0 && <option value="">No universe members</option>}
            {data.selectedUniverseMembers.map((member) => (
              <option key={member.id} value={member.symbol_id}>
                {compactEquitySymbol(data.stockSymbols, member.symbol_id)}
              </option>
            ))}
          </select>
        </label>
        <div className="grid gap-3 md:grid-cols-3">
          <SelectField label="Catalyst type" options={catalystTypes} value={catalystType} onChange={setCatalystType} />
          <SelectField label="Importance" options={importanceValues} value={importance} onChange={setImportance} />
          <SelectField label="Sentiment" options={sentimentValues} value={sentiment} onChange={setSentiment} />
        </div>
        <label className="text-sm font-semibold text-[var(--strong)]">
          Title
          <input
            className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
            value={title}
            maxLength={240}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="text-sm font-semibold text-[var(--strong)]">
          Summary
          <textarea
            className="mt-2 min-h-24 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
            value={summary}
            maxLength={2000}
            onChange={(event) => setSummary(event.target.value)}
          />
        </label>
        <button
          className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!data.workspace || !symbolId || pending}
          type="submit"
        >
          {pending ? "Saving context" : "Add catalyst context"}
        </button>
      </form>
      <div className="mt-4 grid gap-3">
        {data.catalysts.slice(0, 8).map((catalyst) => (
          <div key={catalyst.id} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-[var(--strong)]">{catalyst.title}</p>
                <p className="mt-1 text-xs text-slate-500">
                  {compactEquitySymbol(data.stockSymbols, catalyst.symbol_id)} · {equityLabel(catalyst.catalyst_type)}
                </p>
              </div>
              <Badge value={equityLabel(catalyst.importance)} tone={equityStatusTone(catalyst.importance)} />
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{catalyst.summary}</p>
          </div>
        ))}
        {data.catalysts.length === 0 && (
          <div className="muted-surface rounded-lg p-5 text-sm text-slate-500">
            No catalyst context is stored for this workspace yet.
          </div>
        )}
      </div>
    </Panel>
  );
}

function SelectField({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-sm font-semibold text-[var(--strong)]">
      {label}
      <select
        className="mt-2 w-full rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {equityLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}
