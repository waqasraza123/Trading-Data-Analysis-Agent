"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { reviewJournalEntry } from "@/lib/api/journal";
import type { SignalOutcome } from "@/lib/api/types";
import type { JournalEntryReview } from "@/lib/journal/types";
import { outcomeTone, reviewLabel } from "@/lib/review/labels";
import { Badge } from "@/components/status/badge";
import { Button } from "@/components/ui/Button";
import {
  ReviewField,
  ReviewSurfacePanel,
  reviewInputClassName,
} from "@/components/review-surfaces/ReviewSurface";
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
    <ReviewSurfacePanel
      eyebrow="Outcome reflection"
      title="Review against observed outcome"
      description="Compare the note with deterministic outcome data when a linked outcome is available."
    >
      {outcomes.length > 0 ? (
        <div className="flex flex-wrap items-end gap-3">
          <ReviewField label="Outcome">
            <select
              className={reviewInputClassName("min-w-72")}
              value={outcomeId}
              onChange={(event) => setOutcomeId(event.target.value)}
            >
              {outcomes.map((outcome) => (
                <option key={outcome.id} value={outcome.id}>
                  {outcome.horizon_minutes}m · {reviewLabel(outcome.outcome_label)}
                </option>
              ))}
            </select>
          </ReviewField>
          <Button
            variant="primary"
            type="button"
            loading={pending}
            onClick={submitReview}
          >
            Review note
          </Button>
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
    </ReviewSurfacePanel>
  );
}
