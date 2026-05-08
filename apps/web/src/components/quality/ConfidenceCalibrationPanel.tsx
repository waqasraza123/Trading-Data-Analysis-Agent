import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function ConfidenceCalibrationPanel({ data }: { data: QualityScoreboardData }) {
  if (data.calibrationRows.length === 0) {
    return null;
  }
  return (
    <Panel title="Confidence calibration" eyebrow="Alignment by confidence bin">
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {data.calibrationRows.map((row, index) => (
          <AnimatedListItem
            as="article"
            key={row.id}
            className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{row.binLabel}</h3>
              <Badge value={qualityLabel(row.calibrationLabel)} tone={qualityTone(row.calibrationLabel)} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <Metric label="Horizon" value={`${row.horizonMinutes} minutes`} />
              <Metric label="Sample size" value={String(row.sampleSize)} />
              <Metric label="Alignment score" value={formatPercent(row.alignmentScore)} />
              <Metric label="Average confidence" value={formatPercent(row.averageConfidence)} />
              <Metric label="Continuation" value={formatPercent(row.continuationRate)} />
              <Metric label="Reversal" value={formatPercent(row.reversalRate)} />
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
