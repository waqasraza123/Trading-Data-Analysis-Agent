import Link from "next/link";
import { Panel } from "@/components/layout/panel";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { OutcomeReviewQueueItem } from "@/lib/review/types";

export function JournalPromptPanel({ items, workspaceId }: { items: OutcomeReviewQueueItem[]; workspaceId: string | null | undefined }) {
  const missingJournalItems = items.filter((item) => !item.journalEntry).slice(0, 4);
  if (missingJournalItems.length === 0) {
    return null;
  }
  return (
    <Panel title="Journal prompts" eyebrow="Reflection gaps">
      <div className="space-y-3">
        {missingJournalItems.map((item, index) => (
          <AnimatedListItem
            as="article"
            key={item.id}
            className={cn(
              "flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3",
              motionCardClass,
              motionRevealPresetClass("scale-subtle"),
            )}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <div>
              <p className="text-sm font-semibold text-[var(--strong)]">{item.symbol?.symbol || "Unknown symbol"} · {item.signal.signal.timeframe}</p>
              <p className="mt-1 text-sm text-slate-500">Add a note about what was observed and what needs follow-up review.</p>
            </div>
            <Link
              className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white"
              href={journalHref(workspaceId, item)}
            >
              Create note
            </Link>
          </AnimatedListItem>
        ))}
      </div>
    </Panel>
  );
}

function journalHref(workspaceId: string | null | undefined, item: OutcomeReviewQueueItem): string {
  const params = new URLSearchParams();
  if (workspaceId) {
    params.set("workspaceId", workspaceId);
  }
  params.set("signalId", item.signal.signal.id);
  params.set("analysisRunId", item.signal.analysis_run_id);
  if (item.setupContext) {
    params.set("setupContextId", item.setupContext.id);
  }
  params.set("outcomeId", item.latestOutcome.id);
  return `/journal?${params.toString()}`;
}
