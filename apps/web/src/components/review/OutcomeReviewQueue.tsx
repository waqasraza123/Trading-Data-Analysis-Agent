import type { OutcomeReviewData } from "@/lib/review/types";
import { OutcomeReviewCard } from "./OutcomeReviewCard";
import { OutcomeReviewEmptyState } from "./OutcomeReviewEmptyState";

export function OutcomeReviewQueue({ data }: { data: OutcomeReviewData }) {
  if (data.queue.length === 0) {
    return <OutcomeReviewEmptyState />;
  }
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Review queue</p>
          <h2 className="mt-1 text-lg font-semibold text-[var(--strong)]">Observed outcomes needing daily review</h2>
        </div>
        <p className="text-sm text-slate-500">Loaded {data.queue.length} of {data.allQueue.length} recent outcome items</p>
      </div>
      <div className="space-y-4">
        {data.queue.map((item) => (
          <OutcomeReviewCard key={item.id} item={item} workspaceId={data.workspace?.id} />
        ))}
      </div>
    </section>
  );
}
