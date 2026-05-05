import Link from "next/link";
import { Badge } from "@/components/status/badge";
import {
  ReviewMetricGrid,
  ReviewSurfaceMetric,
  ReviewSurfacePanel,
} from "@/components/review-surfaces/ReviewSurface";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import { diagnosticTone, reviewLabel } from "@/lib/review/labels";
import type { OutcomeReviewData } from "@/lib/review/types";

export function OutcomeReviewSummary({ data }: { data: OutcomeReviewData }) {
  return (
    <ReviewMetricGrid>
      <ReviewSurfaceMetric label="Outcome items" value={data.summary.queueCount} detail="Filtered review queue" tone="info" />
      <ReviewSurfaceMetric label="Reviewed" value={data.summary.reviewedCount} detail="Linked journal notes" tone="good" />
      <ReviewSurfaceMetric label="Needs reflection" value={data.summary.missingJournalCount} detail="No linked journal note" tone={data.summary.missingJournalCount > 0 ? "warning" : "good"} />
      <ReviewSurfaceMetric label="No follow-through" value={data.summary.noFollowThroughCount} detail="Observed outcome category" />
    </ReviewMetricGrid>
  );
}

export function OutcomeReviewJournalPrompts({ data }: { data: OutcomeReviewData }) {
  const missingJournalItems = data.queue.filter((item) => !item.journalEntry).slice(0, 4);
  if (missingJournalItems.length === 0) {
    return null;
  }
  return (
    <ReviewSurfacePanel
      eyebrow="Reflection gaps"
      title="Journal reflections recommended"
      description="Add concise notes to close the loop between deterministic outcome data and operator reflection."
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {missingJournalItems.map((item) => (
          <Link key={item.id} className="muted-surface rounded-lg p-4 transition hover:border-[var(--accent)]" href={journalHref(data.workspace?.id, item)}>
            <p className="text-xs font-semibold uppercase text-slate-500">{item.symbol?.symbol || "Symbol"} · {item.latestOutcome.horizon_minutes}m</p>
            <h3 className="mt-2 text-sm font-semibold text-[var(--strong)]">{reviewLabel(item.latestOutcome.outcome_label)}</h3>
            <p className="mt-2 text-xs leading-5 text-slate-500">Create a reflection note linked to this setup and observed outcome.</p>
          </Link>
        ))}
      </div>
    </ReviewSurfacePanel>
  );
}

export function OutcomeReviewDiagnostics({ data }: { data: OutcomeReviewData }) {
  const profileRows = data.profileDiagnostics.slice(0, 4);
  const patternRows = data.patternDiagnostics.slice(0, 4);
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <ReviewSurfacePanel title="Profile diagnostics" eyebrow="Reliability context">
        {profileRows.length === 0 ? (
          <p className="text-sm text-slate-500">No profile diagnostics returned for this review scope.</p>
        ) : (
          <div className="space-y-3">
            {profileRows.map((item) => (
              <div key={item.id} className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-[var(--strong)]">{qualityLabel(item.strategy_profile_key)}</h3>
                  <Badge value={reviewLabel(item.diagnostic_label)} tone={diagnosticTone(item.diagnostic_label)} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.diagnostic_summary}</p>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                  <span>Sample {item.sample_size}</span>
                  <span>Alignment {formatPercent(item.confidence_alignment_score)}</span>
                  <span>Reversal {formatPercent(item.reversal_rate)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </ReviewSurfacePanel>
      <ReviewSurfacePanel title="Pattern review" eyebrow="Observed behavior">
        {patternRows.length === 0 ? (
          <p className="text-sm text-slate-500">No pattern diagnostics returned for this review scope.</p>
        ) : (
          <div className="space-y-3">
            {patternRows.map((item) => (
              <div key={item.id} className="muted-surface rounded-lg p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-[var(--strong)]">{qualityLabel(item.pattern_type)}</h3>
                  <Badge value={reviewLabel(item.diagnostic_label)} tone={qualityTone(item.diagnostic_label)} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.diagnostic_summary}</p>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                  <span>Sample {item.sample_size}</span>
                  <span>No follow-through {formatPercent(item.no_follow_through_rate)}</span>
                  <span>Reversal {formatPercent(item.reversal_rate)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </ReviewSurfacePanel>
    </div>
  );
}

function journalHref(workspaceId: string | null | undefined, item: OutcomeReviewData["queue"][number]): string {
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
