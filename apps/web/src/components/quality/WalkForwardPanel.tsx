import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { formatPercent, qualityLabel, qualityTone } from "@/lib/quality/labels";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function WalkForwardPanel({ data }: { data: QualityScoreboardData }) {
  if (data.walkForwardRows.length === 0) {
    return null;
  }
  return (
    <Panel title="Walk-forward validation" eyebrow="Window stability">
      <div className="space-y-3">
        {data.walkForwardRows.map((row, index) => (
          <AnimatedListItem
            as="article"
            key={row.id}
            className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-[var(--strong)]">{row.windowLabel}</h3>
                <p className="mt-1 text-xs text-slate-500">{row.horizonMinutes} minute horizon · {row.sampleSize} sample size</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge value={qualityLabel(row.stabilityLabel)} tone={qualityTone(row.stabilityLabel)} />
                <Badge value={row.trendLabel} tone={qualityTone(row.trendLabel)} />
              </div>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{row.summary}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-300">
              <span>Continuation {formatPercent(row.continuationRate)}</span>
              <span>Reversal {formatPercent(row.reversalRate)}</span>
            </div>
          </AnimatedListItem>
        ))}
      </div>
    </Panel>
  );
}
