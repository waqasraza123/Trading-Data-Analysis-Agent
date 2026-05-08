import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function PatternAttributionPanel({ data }: { data: QualityScoreboardData }) {
  if (data.patternRows.length === 0) {
    return null;
  }
  return (
    <Panel title="Pattern attribution" eyebrow="Selected, rejected, and blocking behavior">
      <div className="grid gap-4 lg:grid-cols-2">
        {data.patternRows.map((row, index) => (
          <AnimatedListItem
            as="article"
            key={row.patternType}
            className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{qualityLabel(row.patternType)}</h3>
              <Badge value={qualityLabel(row.diagnosticLabel)} tone={qualityTone(row.diagnosticLabel)} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{row.summary}</p>
            <div className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <Metric label="Selected" value={String(row.selectedCount)} />
              <Metric label="Rejected" value={String(row.rejectedCount)} />
              <Metric label="Blocking" value={String(row.blockedCount)} />
              <Metric label="Continuation" value={formatPercent(row.continuationRate)} />
              <Metric label="Reversal" value={formatPercent(row.reversalRate)} />
              <Metric label="No follow-through" value={formatPercent(row.noFollowThroughRate)} />
            </div>
            <p className="mt-3 text-xs text-slate-500">{row.observedOutcomes}</p>
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
