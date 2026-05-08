"use client";

import { type FormEvent, useState } from "react";
import { Panel } from "@/components/layout/panel";
import { Badge, toneForQuality } from "@/components/status/badge";
import type { JournalEntry, UUID } from "@/lib/api/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import { setupLabel, sanitizeSetupText } from "@/lib/setup-detail/labels";
import { SetupEmptySection } from "./SetupEmptySection";

const decisionTypes = [
  "observed",
  "ignored",
  "reviewed",
  "paper_followed",
  "external_action_taken",
  "no_action",
  "uncertain",
];

type SetupJournalPanelProps = {
  apiBaseUrl: string;
  workspaceId: UUID | null;
  signalId: UUID;
  analysisRunId: UUID | null;
  setupContextId: UUID | null;
  entries: JournalEntry[];
};

export function SetupJournalPanel({
  apiBaseUrl,
  workspaceId,
  signalId,
  analysisRunId,
  setupContextId,
  entries,
}: SetupJournalPanelProps) {
  const [decisionType, setDecisionType] = useState("reviewed");
  const [title, setTitle] = useState("Setup review note");
  const [userNotes, setUserNotes] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "failed">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const canSubmit = Boolean(workspaceId && title.trim() && userNotes.trim() && status !== "saving");
  const normalizedBaseUrl = apiBaseUrl.replace(/\/$/, "");

  async function submitJournalEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspaceId || !canSubmit) {
      return;
    }
    setStatus("saving");
    setErrorMessage("");
    const response = await fetch(`${normalizedBaseUrl}/journal-entries`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        workspaceId,
        signalId,
        analysisRunId,
        setupContextId,
        title: title.trim(),
        status: "saved",
        decisionType,
        userNotes: userNotes.trim(),
        tags: ["setup-detail"],
        metadata: {
          source: "setup_detail_view",
        },
      }),
    });
    if (!response.ok) {
      setStatus("failed");
      setErrorMessage("Journal note could not be saved.");
      return;
    }
    setStatus("saved");
    setUserNotes("");
  }

  return (
    <Panel title="Journal" eyebrow="Decision note feedback">
      <div className="space-y-5">
        <form className="grid gap-3" onSubmit={submitJournalEntry}>
          <div className="grid gap-3 md:grid-cols-2">
            <label className="grid gap-1 text-sm">
              <span className="text-xs font-semibold uppercase text-slate-500">Decision type</span>
              <select
                value={decisionType}
                onChange={(event) => setDecisionType(event.target.value)}
                className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
              >
                {decisionTypes.map((value) => (
                  <option key={value} value={value}>
                    {setupLabel(value)}
                  </option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-sm">
              <span className="text-xs font-semibold uppercase text-slate-500">Title</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                maxLength={240}
                className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
              />
            </label>
          </div>
          <label className="grid gap-1 text-sm">
            <span className="text-xs font-semibold uppercase text-slate-500">Journal note</span>
            <textarea
              value={userNotes}
              onChange={(event) => setUserNotes(event.target.value)}
              maxLength={8000}
              rows={4}
              className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
            />
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={!canSubmit}
              className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              Save journal note
            </button>
            {status === "saved" && <span className="text-sm text-teal-700 dark:text-teal-200">Journal note saved.</span>}
            {status === "failed" && <span className="text-sm text-red-700 dark:text-red-200">{errorMessage}</span>}
            {!workspaceId && <span className="text-sm text-slate-500">Workspace context is required to save a note.</span>}
          </div>
        </form>
        {entries.length === 0 ? (
          <SetupEmptySection title="No journal entries" message="No journal notes were returned for this signal." />
        ) : (
          <div className="space-y-3">
            {entries.map((entry, index) => (
              <AnimatedListItem as="article" key={entry.id} style={motionRevealDensityStyle(index, "compact")}>
                <div className="muted-surface rounded-lg p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-sm font-semibold text-[var(--strong)]">{sanitizeSetupText(entry.title)}</h3>
                    <Badge value={entry.decision_type} tone={toneForQuality(entry.status)} />
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{sanitizeSetupText(entry.user_notes)}</p>
                  <p className="mt-2 text-xs text-slate-500">Saved {formatDateTime(entry.created_at)}</p>
                </div>
              </AnimatedListItem>
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}
