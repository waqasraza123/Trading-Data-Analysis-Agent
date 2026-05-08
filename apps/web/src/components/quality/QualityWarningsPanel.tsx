import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import type { QualityScoreboardData } from "@/lib/quality/types";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function QualityWarningsPanel({ data }: { data: QualityScoreboardData }) {
  if (data.warnings.length === 0) {
    return null;
  }
  return (
    <Panel title="Quality warnings" eyebrow="Review notes">
      <div className="grid gap-3 lg:grid-cols-2">
        {data.warnings.map((warning, index) => (
          <AnimatedListItem
            as="article"
            key={warning.id}
            className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold text-[var(--strong)]">{warning.title}</h3>
              <Badge value={warning.severity} tone={warning.severity} />
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{warning.detail}</p>
          </AnimatedListItem>
        ))}
      </div>
    </Panel>
  );
}
