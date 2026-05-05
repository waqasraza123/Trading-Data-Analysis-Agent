import Link from "next/link";
import { Badge } from "@/components/status/badge";
import { ReviewSurfacePanel } from "@/components/review-surfaces/ReviewSurface";
import { formatPercent, qualityLabel } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";

type FocusTone = "info" | "warning" | "danger";

type FocusItem = {
  id: string;
  title: string;
  detail: string;
  tone: FocusTone;
  meta: string;
};

export function QualityReviewFocusPanel({ data }: { data: QualityScoreboardData }) {
  const focusItems: FocusItem[] = [
    ...data.warnings.map((warning) => ({
      id: warning.id,
      title: warning.title,
      detail: warning.detail,
      tone: warning.severity as FocusTone,
      meta: "Quality warning",
    })),
    ...data.profileRows
      .filter((row) => row.recommendationStatus || row.sampleSize < 10)
      .slice(0, 3)
      .map((row) => ({
        id: `profile-${row.key}`,
        title: qualityLabel(row.key),
        detail: row.sampleSize < 10 ? "Sample size is low for this profile." : row.summary,
        tone: row.sampleSize < 10 ? "warning" as const : "info" as const,
        meta: `Alignment ${formatPercent(row.confidenceAlignment)}`,
      })),
    ...data.cohortDriftRows
      .filter((row) => row.severity !== "none" && row.driftLabel !== "stable")
      .slice(0, 3)
      .map((row) => ({
        id: `drift-${row.id}`,
        title: row.affectedCohort,
        detail: row.summary,
        tone: "warning" as const,
        meta: qualityLabel(row.driftLabel),
      })),
  ].slice(0, 6);

  if (focusItems.length === 0) {
    return (
      <ReviewSurfacePanel title="What to review" eyebrow="Daily focus">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          No immediate quality warnings matched the current filters. Continue with outcome review or broaden the quality scope.
        </p>
      </ReviewSurfacePanel>
    );
  }

  return (
    <ReviewSurfacePanel
      title="What to review"
      eyebrow="Daily focus"
      description="Prioritized diagnostics, sample-size warnings, and drift findings for operator review."
      action={<Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800" href={data.workspace ? `/review/outcomes?workspaceId=${data.workspace.id}` : "/review/outcomes"}>Open outcome review</Link>}
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {focusItems.map((item) => (
          <div key={item.id} className="muted-surface rounded-lg p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{item.title}</h3>
              <Badge value={item.meta} tone={item.tone} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
          </div>
        ))}
      </div>
    </ReviewSurfacePanel>
  );
}
