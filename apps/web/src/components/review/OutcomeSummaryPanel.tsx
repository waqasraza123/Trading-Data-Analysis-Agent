import { MetricCard, Panel } from "@/components/layout/panel";
import type { OutcomeReviewData } from "@/lib/review/types";

export function OutcomeSummaryPanel({ data }: { data: OutcomeReviewData }) {
  return (
    <Panel title="Review summary" eyebrow="Current queue">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <MetricCard label="Outcome items" value={String(data.summary.queueCount)} detail="Filtered review queue" />
        <MetricCard label="With notes" value={String(data.summary.reviewedCount)} detail="Linked journal entries" />
        <MetricCard label="Needs note" value={String(data.summary.missingJournalCount)} detail="No linked journal entry" />
        <MetricCard label="Continuation" value={String(data.summary.continuationCount)} detail="Observed outcome label" />
        <MetricCard label="Reversal" value={String(data.summary.reversalCount)} detail="Observed outcome label" />
        <MetricCard label="No follow-through" value={String(data.summary.noFollowThroughCount)} detail="Observed outcome label" />
      </div>
    </Panel>
  );
}
