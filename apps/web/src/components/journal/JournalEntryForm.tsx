"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import {
  ReviewField,
  ReviewSurfacePanel,
  reviewInputClassName,
} from "@/components/review-surfaces/ReviewSurface";
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
    <form onSubmit={submitEntry}>
      <ReviewSurfacePanel
        eyebrow={entry ? "Edit note" : "Create note"}
        title="Journal reflection"
        description="Capture observation context, bias, and follow-up notes. Account-result, order, margin, and sizing fields are intentionally excluded."
      >
      {message && <p className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      <div className="grid gap-3 md:grid-cols-2">
        <ReviewField label="Title">
          <input
            className={reviewInputClassName()}
            maxLength={240}
            value={title}
            onChange={(event) => setTitle(event.target.value)}
          />
        </ReviewField>
        <ReviewField label="Decision type">
          <select
            className={reviewInputClassName()}
            value={decisionType}
            onChange={(event) => setDecisionType(event.target.value as JournalDecisionType)}
          >
            {journalDecisionTypes.map((value) => (
              <option key={value} value={value}>{reviewLabel(value)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Observed bias">
          <select
            className={reviewInputClassName()}
            value={userBias}
            onChange={(event) => setUserBias(event.target.value as JournalUserBias | "")}
          >
            <option value="">Not specified</option>
            {journalUserBiases.map((value) => (
              <option key={value} value={value}>{reviewLabel(value)}</option>
            ))}
          </select>
        </ReviewField>
        <ReviewField label="Signal link">
          <input
            className={reviewInputClassName()}
            value={signalId}
            onChange={(event) => setSignalId(event.target.value)}
            placeholder="Optional signal ID"
          />
        </ReviewField>
        <ReviewField label="Setup context link">
          <input
            className={reviewInputClassName()}
            value={setupContextId}
            onChange={(event) => setSetupContextId(event.target.value)}
            placeholder="Optional setup context ID"
          />
        </ReviewField>
        <ReviewField label="Tags">
          <input
            className={reviewInputClassName()}
            value={tagsText}
            onChange={(event) => setTagsText(event.target.value)}
            placeholder="review, follow-up"
          />
        </ReviewField>
      </div>
      <ReviewField label="Notes">
        <textarea
          className={reviewInputClassName("mt-1 min-h-36 resize-y")}
          maxLength={8000}
          value={userNotes}
          onChange={(event) => setUserNotes(event.target.value)}
        />
      </ReviewField>
      <Button
        className="mt-4"
        variant="primary"
        type="submit"
        loading={pending}
        disabled={!canSubmit}
      >
        {entry ? "Update note" : "Save note"}
      </Button>
      </ReviewSurfacePanel>
    </form>
  );
}

function defaultTitle(outcomeId: string | undefined): string {
  return outcomeId ? "Outcome review note" : "Journal review note";
}
