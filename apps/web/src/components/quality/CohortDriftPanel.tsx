import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function CohortDriftPanel({ data }: { data: QualityScoreboardData }) {
  if (data.cohortDriftRows.length === 0) {
    return null;
  }
  return (
    <Panel title="Cohort drift" eyebrow="Baseline versus recent behavior">
      <div className="grid gap-4 lg:grid-cols-2">
        {data.cohortDriftRows.map((row, index) => (
          <AnimatedListItem
            as="article"
            key={row.id}
            className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{row.affectedCohort}</h3>
              <div className="flex flex-wrap gap-2">
                <Badge value={qualityLabel(row.driftLabel)} tone={qualityTone(row.driftLabel)} />
                <Badge value={qualityLabel(row.severity)} tone={qualityTone(row.severity)} />
              </div>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{row.summary}</p>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
              <Metric label="Baseline sample" value={String(row.baselineSampleSize)} />
              <Metric label="Recent sample" value={String(row.recentSampleSize)} />
              <Metric label="Baseline continuation" value={formatPercent(row.baselineContinuationRate)} />
              <Metric label="Recent continuation" value={formatPercent(row.recentContinuationRate)} />
              <Metric label="Baseline reversal" value={formatPercent(row.baselineReversalRate)} />
              <Metric label="Recent reversal" value={formatPercent(row.recentReversalRate)} />
            </div>
          </AnimatedListItem>
        ))}
      </div>
    </Panel>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-[var(--strong)]">{value}</p>
    </div>
  );
}
