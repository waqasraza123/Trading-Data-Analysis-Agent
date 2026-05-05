import Link from "next/link";
import { Badge } from "@/components/status/badge";
import {
  ReviewFact,
  ReviewMetricGrid,
  ReviewSurfacePanel,
} from "@/components/review-surfaces/ReviewSurface";
import type { JournalEntryWithReviews } from "@/lib/journal/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { shortIdentifier } from "@/lib/formatting/labels";
import { reviewLabel } from "@/lib/review/labels";
import { JournalEntryForm } from "./JournalEntryForm";
import { JournalReviewPanel } from "./JournalReviewPanel";
import type { JournalData } from "@/lib/journal/types";

export function JournalEntryDetail({ data, selectedEntry }: { data: JournalData; selectedEntry: JournalEntryWithReviews }) {
  const entry = selectedEntry.entry;
  return (
    <div className="space-y-5">
      <ReviewSurfacePanel
        title={entry.title}
        eyebrow="Journal detail"
        action={<Badge value={entry.status} />}
      >
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{entry.user_notes}</p>
        <ReviewMetricGrid className="mt-4 xl:grid-cols-3">
          <ReviewFact label="Decision type" value={reviewLabel(entry.decision_type)} />
          <ReviewFact label="Observed bias" value={entry.user_bias ? reviewLabel(entry.user_bias) : "Not specified"} />
          <ReviewFact label="Updated" value={formatDateTime(entry.updated_at)} />
        </ReviewMetricGrid>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          {entry.signal_id && (
            <Link className="rounded-md border border-[var(--line)] px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800" href={`/signals/${entry.signal_id}`}>
              Signal {shortIdentifier(entry.signal_id)}
            </Link>
          )}
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800" href={data.workspace ? `/journal?workspaceId=${data.workspace.id}` : "/journal"}>
            All notes
          </Link>
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-800" href={data.workspace ? `/review/outcomes?workspaceId=${data.workspace.id}` : "/review/outcomes"}>
            Outcome review
          </Link>
        </div>
      </ReviewSurfacePanel>
      <JournalReviewPanel
        entryId={entry.id}
        reviews={selectedEntry.reviews}
        outcomes={selectedEntry.outcomes}
        defaultOutcomeId={data.filters.outcomeId}
      />
      <JournalEntryForm data={data} entry={entry} />
    </div>
  );
}
