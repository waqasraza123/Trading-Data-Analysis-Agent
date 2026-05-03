import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
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
      <Panel
        title={entry.title}
        eyebrow="Journal detail"
        action={<Badge value={entry.status} />}
      >
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{entry.user_notes}</p>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <Fact label="Decision type" value={reviewLabel(entry.decision_type)} />
          <Fact label="User bias" value={entry.user_bias ? reviewLabel(entry.user_bias) : "Not specified"} />
          <Fact label="Updated" value={formatDateTime(entry.updated_at)} />
        </div>
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
      </Panel>
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

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="muted-surface rounded-lg p-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-medium text-[var(--strong)]">{value}</p>
    </div>
  );
}
