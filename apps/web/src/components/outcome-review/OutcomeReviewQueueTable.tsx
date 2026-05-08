import Link from "next/link";
import { cn } from "@/lib/ui/cn";
import { Badge, toneForBias } from "@/components/status/badge";
import {
  ReviewSurfaceEmptyState,
  ReviewSurfacePanel,
  ReviewTable,
} from "@/components/review-surfaces/ReviewSurface";
import { formatDateTime } from "@/lib/formatting/dates";
import { shortIdentifier } from "@/lib/formatting/labels";
import { motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import { outcomeTone, reviewLabel } from "@/lib/review/labels";
import type { OutcomeReviewData, OutcomeReviewQueueItem } from "@/lib/review/types";

export function OutcomeReviewQueueTable({ data }: { data: OutcomeReviewData }) {
  if (data.queue.length === 0) {
    return (
      <ReviewSurfaceEmptyState
        title="No outcomes matched"
        message="Broaden the filters or run the backend outcome evaluation workflow before daily review."
      />
    );
  }
  return (
    <ReviewSurfacePanel
      eyebrow="Review queue"
      title="Outcomes ready for reflection"
      description={`Loaded ${data.queue.length} of ${data.allQueue.length} recent outcome items.`}
    >
      <ReviewTable>
        <thead className="bg-[var(--panel-muted)] text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-3">Setup</th>
            <th className="px-3 py-3">Outcome</th>
            <th className="px-3 py-3">Horizons</th>
            <th className="px-3 py-3">Reflection</th>
            <th className="px-3 py-3">Updated</th>
            <th className="px-3 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.queue.map((item, index) => (
            <tr
              key={item.id}
              className={cn("border-t border-[var(--line)] align-top", motionCardClass, motionRevealPresetClass("scale-subtle"))}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <td className="px-3 py-4">
                <div className="min-w-64">
                  <p className="font-medium text-[var(--strong)]">{item.symbol?.symbol || shortIdentifier(item.signal.signal.symbol_id)} · {item.signal.signal.timeframe}</p>
                  <p className="mt-1 max-w-md text-xs leading-5 text-slate-500">{item.signal.signal.summary || "Stored deterministic setup context"}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Badge value={item.signal.signal.bias} tone={toneForBias(item.signal.signal.bias)} />
                    {item.signal.signal.pattern_type && <Badge value={reviewLabel(item.signal.signal.pattern_type)} tone="neutral" />}
                  </div>
                </div>
              </td>
              <td className="px-3 py-4">
                <Badge value={reviewLabel(item.latestOutcome.outcome_label)} tone={outcomeTone(item.latestOutcome.outcome_label)} />
                <p className="mt-2 text-xs text-slate-500">{reviewLabel(item.latestOutcome.evaluation_status)}</p>
              </td>
              <td className="px-3 py-4">
                <div className="flex flex-wrap gap-2">
                  {item.outcomes.map((outcome) => (
                    <span key={outcome.id} className="rounded-md border border-[var(--line)] bg-[var(--panel-muted)] px-2 py-1 text-xs text-slate-600 dark:text-slate-300">
                      {outcome.horizon_minutes}m · {reviewLabel(outcome.outcome_label)}
                    </span>
                  ))}
                </div>
              </td>
              <td className="px-3 py-4">
                {item.journalEntry ? (
                  <Link className="font-medium text-[var(--accent)]" href={`/journal/${item.journalEntry.id}`}>{item.journalEntry.title}</Link>
                ) : (
                  <span className="text-slate-500">Reflection recommended</span>
                )}
              </td>
              <td className="px-3 py-4 text-slate-600 dark:text-slate-300">{formatDateTime(item.latestOutcome.updated_at)}</td>
              <td className="px-3 py-4">
                <div className="flex min-w-40 flex-wrap gap-2">
                  <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-xs font-semibold hover:bg-slate-100 dark:hover:bg-slate-800" href={`/signals/${item.signal.signal.id}`}>
                    Signal detail
                  </Link>
                  <Link className="rounded-md bg-[var(--accent)] px-3 py-2 text-xs font-semibold text-white" href={journalHref(data.workspace?.id, item)}>
                    {item.journalEntry ? "Open note" : "Add note"}
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </ReviewTable>
    </ReviewSurfacePanel>
  );
}

function journalHref(workspaceId: string | null | undefined, item: OutcomeReviewQueueItem): string {
  if (item.journalEntry) {
    return `/journal/${item.journalEntry.id}`;
  }
  const params = new URLSearchParams();
  if (workspaceId) {
    params.set("workspaceId", workspaceId);
  }
  params.set("signalId", item.signal.signal.id);
  params.set("analysisRunId", item.signal.analysis_run_id);
  params.set("outcomeId", item.latestOutcome.id);
  if (item.setupContext) {
    params.set("setupContextId", item.setupContext.id);
  }
  return `/journal?${params.toString()}`;
}
