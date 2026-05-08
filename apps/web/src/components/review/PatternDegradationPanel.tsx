import { Badge } from "@/components/status/badge";
import { Panel } from "@/components/layout/panel";
import { diagnosticTone, reviewLabel } from "@/lib/review/labels";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import { cn } from "@/lib/ui/cn";
import type { OutcomeReviewData } from "@/lib/review/types";

export function PatternDegradationPanel({ data }: { data: OutcomeReviewData }) {
  const diagnostics = data.patternDiagnostics.slice(0, 5);
  const attribution = data.patternAttributionResults.slice(0, 5);
  if (diagnostics.length === 0 && attribution.length === 0) {
    return null;
  }
  return (
    <Panel title="Pattern reliability" eyebrow="Optional diagnostics">
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          {diagnostics.length === 0 ? (
            <p className="text-sm text-slate-500">No pattern diagnostics returned.</p>
          ) : (
            diagnostics.map((item, index) => (
              <AnimatedListItem
                as="article"
                key={item.id}
                className={cn("muted-surface rounded-lg p-4", motionCardClass)}
                preset="scale-subtle"
                style={motionRevealDensityStyle(index, "compact")}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-[var(--strong)]">{reviewLabel(item.pattern_type)}</h3>
                  <Badge value={item.diagnostic_label} tone={diagnosticTone(item.diagnostic_label)} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.diagnostic_summary}</p>
                <p className="mt-2 text-xs text-slate-500">{item.evaluated_count} evaluated outcomes · {item.horizon_minutes} minute horizon</p>
              </AnimatedListItem>
            ))
          )}
        </div>
        <div className="space-y-3">
          {attribution.length === 0 ? (
            <p className="text-sm text-slate-500">No pattern attribution results returned.</p>
          ) : (
            attribution.map((item, index) => (
              <AnimatedListItem
                as="article"
                key={item.id}
                className={cn("muted-surface rounded-lg p-4", motionCardClass)}
                preset="scale-subtle"
                style={motionRevealDensityStyle(index, "compact")}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-[var(--strong)]">{reviewLabel(item.pattern_type)}</h3>
                  <Badge value={item.attribution_label} tone={diagnosticTone(item.attribution_label)} />
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.diagnostic_summary}</p>
                <p className="mt-2 text-xs text-slate-500">{item.candidate_count} candidates · {item.selected_count} selected contexts</p>
              </AnimatedListItem>
            ))
          )}
        </div>
      </div>
    </Panel>
  );
}
