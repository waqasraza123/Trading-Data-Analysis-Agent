"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { createJournalEntry, updateJournalEntry } from "@/lib/api/journal";
import type { JournalEntry } from "@/lib/api/types";
import { journalDecisionTypes, journalUserBiases, type JournalData, type JournalDecisionType, type JournalUserBias } from "@/lib/journal/types";
import { reviewLabel } from "@/lib/review/labels";

type JournalEntryFormProps = {
  data: JournalData;
  entry?: JournalEntry | null;
};

export function JournalEntryForm({ data, entry }: JournalEntryFormProps) {
  const router = useRouter();
  const workspaceId = data.workspace?.id || "";
  const [title, setTitle] = useState(entry?.title || defaultTitle(data.filters.outcomeId));
  const [decisionType, setDecisionType] = useState<JournalDecisionType>((entry?.decision_type as JournalDecisionType) || "reviewed");
  const [userBias, setUserBias] = useState<JournalUserBias | "">((entry?.user_bias as JournalUserBias) || "");
  const [userNotes, setUserNotes] = useState(entry?.user_notes || "");
  const [tagsText, setTagsText] = useState((entry?.tags || []).join(", "));
  const [signalId, setSignalId] = useState(entry?.signal_id || data.filters.signalId || "");
  const [setupContextId, setSetupContextId] = useState(entry?.setup_context_id || data.filters.setupContextId || "");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const tags = useMemo(
    () => tagsText.split(",").map((tag) => tag.trim()).filter(Boolean).slice(0, 50),
    [tagsText],
  );
  const canSubmit = Boolean(workspaceId && title.trim() && userNotes.trim() && !pending);

  async function submitEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit) {
      setMessage("Workspace, title, and notes are required.");
      return;
    }
    setPending(true);
    setMessage(null);
    const payload = {
      signalId: signalId || null,
      analysisRunId: entry?.analysis_run_id || data.filters.analysisRunId || null,
      setupContextId: setupContextId || null,
      title: title.trim(),
      status: "saved" as const,
      decisionType,
      userBias: userBias || null,
      userNotes: userNotes.trim(),
      tags,
      metadata: {
        source: entry ? "journal_edit" : "journal_page",
        linkedOutcomeId: data.filters.outcomeId || null,
      },
    };
    const result = entry
      ? await updateJournalEntry(entry.id, payload)
      : await createJournalEntry({ ...payload, workspaceId });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    if (!entry) {
      setTitle(defaultTitle(data.filters.outcomeId));
      setUserNotes("");
      setTagsText("");
    }
    setMessage(entry ? "Journal note updated." : "Journal note saved.");
    router.refresh();
  }

  return (
    <form className="surface rounded-lg p-5" onSubmit={submitEntry}>
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase text-slate-500">{entry ? "Edit note" : "Create journal entry"}</p>
        <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Reflection note</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">Capture observations, bias, and follow-up context. Account metrics, order fields, margin fields, and sizing are intentionally excluded.</p>
      </div>
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">Title</span>
          <input
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            maxLength={240}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">Decision type</span>
          <select
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            value={decisionType}
            onChange={(event) => setDecisionType(event.target.value as JournalDecisionType)}
          >
            {journalDecisionTypes.map((value) => (
              <option key={value} value={value}>{reviewLabel(value)}</option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">User bias</span>
          <select
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            value={userBias}
            onChange={(event) => setUserBias(event.target.value as JournalUserBias | "")}
          >
            <option value="">Not specified</option>
            {journalUserBiases.map((value) => (
              <option key={value} value={value}>{reviewLabel(value)}</option>
            ))}
          </select>
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">Signal link</span>
          <input
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            value={signalId}
            onChange={(event) => setSignalId(event.target.value)}
            placeholder="Optional signal ID"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">Setup context link</span>
          <input
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            value={setupContextId}
            onChange={(event) => setSetupContextId(event.target.value)}
            placeholder="Optional setup context ID"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="text-xs font-semibold uppercase text-slate-500">Tags</span>
          <input
            className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            value={tagsText}
            onChange={(event) => setTagsText(event.target.value)}
            placeholder="review, follow-up"
          />
        </label>
      </div>
      <label className="mt-3 grid gap-1 text-sm">
        <span className="text-xs font-semibold uppercase text-slate-500">Notes</span>
        <textarea
          className="min-h-36 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
          maxLength={8000}
          value={userNotes}
          onChange={(event) => setUserNotes(event.target.value)}
        />
      </label>
      <button
        className="mt-4 rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        disabled={!canSubmit}
      >
        {pending ? "Saving" : entry ? "Update note" : "Save note"}
      </button>
    </form>
  );
}

function defaultTitle(outcomeId: string | undefined): string {
  return outcomeId ? "Outcome review note" : "Journal review note";
}
