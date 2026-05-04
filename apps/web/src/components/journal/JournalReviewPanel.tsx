"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { reviewJournalEntry } from "@/lib/api/journal";
import type { SignalOutcome } from "@/lib/api/types";
import type { JournalEntryReview } from "@/lib/journal/types";
import { outcomeTone, reviewLabel } from "@/lib/review/labels";
import { Badge } from "@/components/status/badge";
import { JournalReflectionBadge } from "./JournalReflectionBadge";

type JournalReviewPanelProps = {
  entryId: string;
  reviews: JournalEntryReview[];
  outcomes: SignalOutcome[];
  defaultOutcomeId?: string;
};

export function JournalReviewPanel({ entryId, reviews, outcomes, defaultOutcomeId }: JournalReviewPanelProps) {
  const router = useRouter();
  const [outcomeId, setOutcomeId] = useState(defaultOutcomeId || outcomes[0]?.id || "");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submitReview() {
    setPending(true);
    setMessage(null);
    const result = await reviewJournalEntry(entryId, { outcomeId: outcomeId || null });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    setMessage("Journal note reviewed against observed outcome.");
    router.refresh();
  }

  return (
    <section className="surface rounded-lg p-5">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase text-slate-500">Outcome reflection</p>
        <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Review against observed outcome</h2>
      </div>
      {outcomes.length > 0 ? (
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid min-w-72 gap-1 text-sm">
            <span className="text-xs font-semibold uppercase text-slate-500">Outcome</span>
            <select
              className="rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-[var(--strong)]"
              value={outcomeId}
              onChange={(event) => setOutcomeId(event.target.value)}
            >
              {outcomes.map((outcome) => (
                <option key={outcome.id} value={outcome.id}>
                  {outcome.horizon_minutes}m · {reviewLabel(outcome.outcome_label)}
                </option>
              ))}
            </select>
          </label>
          <button
            className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            type="button"
            disabled={pending}
            onClick={submitReview}
          >
            {pending ? "Reviewing" : "Review note"}
          </button>
        </div>
      ) : (
        <p className="text-sm leading-6 text-slate-500">No linked outcomes are available for this journal entry yet.</p>
      )}
      {message && <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100">{message}</p>}
      {outcomes.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {outcomes.map((outcome) => (
            <Badge key={outcome.id} value={`${outcome.horizon_minutes}m ${reviewLabel(outcome.outcome_label)}`} tone={outcomeTone(outcome.outcome_label)} />
          ))}
        </div>
      )}
      <div className="mt-5 space-y-3">
        {reviews.length === 0 ? (
          <p className="text-sm leading-6 text-slate-500">No reflection review has been created for this note.</p>
        ) : (
          reviews.map((review) => (
            <div key={review.id} className="muted-surface rounded-lg p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-sm font-semibold text-[var(--strong)]">{reviewLabel(review.outcome_label)}</h3>
                <JournalReflectionBadge value={review.reflection_label} />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{review.reflection_notes}</p>
              {review.lessons.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {review.lessons.map((lesson) => (
                    <span key={lesson} className="rounded-md border border-[var(--line)] px-2 py-1 text-xs text-slate-500">{lesson}</span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </section>
  );
}
