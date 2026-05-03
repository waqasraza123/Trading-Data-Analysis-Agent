import Link from "next/link";
import { Badge, toneForBias } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { shortIdentifier } from "@/lib/formatting/labels";
import { describeObservedOutcome, outcomeTone, reviewLabel } from "@/lib/review/labels";
import type { OutcomeReviewQueueItem } from "@/lib/review/types";

export function OutcomeReviewCard({ item, workspaceId }: { item: OutcomeReviewQueueItem; workspaceId: string | null | undefined }) {
  const signal = item.signal.signal;
  return (
    <article className="surface rounded-lg p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">{item.symbol?.symbol || shortIdentifier(signal.symbol_id)} · {signal.timeframe}</p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--strong)]">{signal.summary || "Stored deterministic signal"}</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge value={signal.bias} tone={toneForBias(signal.bias)} />
          <Badge value={item.latestOutcome.outcome_label} tone={outcomeTone(item.latestOutcome.outcome_label)} />
        </div>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
        {describeObservedOutcome(item.latestOutcome.outcome_label)}
      </p>
      <div className="mt-4 grid gap-3 md:grid-cols-4">
        <Fact label="Horizon" value={`${item.latestOutcome.horizon_minutes} minutes`} />
        <Fact label="Evaluation" value={reviewLabel(item.latestOutcome.evaluation_status)} />
        <Fact label="Pattern" value={reviewLabel(signal.pattern_type)} />
        <Fact label="Updated" value={formatDateTime(item.latestOutcome.updated_at)} />
      </div>
      {item.outcomes.length > 1 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {item.outcomes.map((outcome) => (
            <span key={outcome.id} className="rounded-md border border-[var(--line)] px-2.5 py-1 text-xs text-slate-600 dark:text-slate-300">
              {outcome.horizon_minutes}m · {reviewLabel(outcome.outcome_label)}
            </span>
          ))}
        </div>
      )}
      {item.digestItems.length > 0 && (
        <div className="mt-4 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-900 dark:bg-blue-950 dark:text-blue-100">
          Digest context: {item.digestItems[0].title}
        </div>
      )}
      <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] pt-4">
        <div className="text-sm text-slate-500">
          {item.journalEntry ? (
            <span>Linked note: {item.journalEntry.title}</span>
          ) : (
            <span>No linked journal note yet.</span>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800" href={`/signals/${signal.id}`}>
            Signal detail
          </Link>
          {item.journalEntry ? (
            <Link className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white" href={`/journal/${item.journalEntry.id}`}>
              Review note
            </Link>
          ) : (
            <Link className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white" href={journalHref(workspaceId, item)}>
              Create note
            </Link>
          )}
        </div>
      </div>
    </article>
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

function journalHref(workspaceId: string | null | undefined, item: OutcomeReviewQueueItem): string {
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
