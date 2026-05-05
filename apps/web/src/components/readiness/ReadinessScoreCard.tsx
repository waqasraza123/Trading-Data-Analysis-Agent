import { MetricCard, Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import {
  checksByStatus,
  readinessLabelText,
  readinessLabelTone,
  readinessScorePercent,
} from "@/lib/readiness/labels";
import type { ProductReadinessRun } from "@/lib/readiness/types";

export function ReadinessScoreCard({ run }: { run: ProductReadinessRun }) {
  const counts = checksByStatus(run.checks_json);
  return (
    <Panel
      title="Readiness score"
      eyebrow={`Version ${run.readiness_version}`}
      action={<Badge value={readinessLabelText(run.readiness_label)} tone={readinessLabelTone(run.readiness_label)} />}
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(220px,320px)_1fr]">
        <div className="muted-surface rounded-lg p-5">
          <p className="text-xs font-semibold uppercase text-slate-500">Score</p>
          <p className="mt-3 text-5xl font-semibold text-[var(--strong)]">{readinessScorePercent(run)}</p>
          <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{run.summary}</p>
          <p className="mt-3 text-xs text-slate-500">Checked {formatDateTime(run.created_at)}</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Passed" value={String(counts.passed)} />
          <MetricCard label="Warnings" value={String(counts.warning)} />
          <MetricCard label="Failed" value={String(counts.failed)} />
          <MetricCard label="Skipped" value={String(counts.skipped)} />
        </div>
      </div>
    </Panel>
  );
}
