import { EmptyState } from "@/components/empty-states/empty-state";
import type { SignalConfidenceComponent } from "@/lib/api/types";
import { formatDecimal, formatPercent } from "@/lib/formatting/numbers";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";

export function ConfidenceList({ components }: { components: SignalConfidenceComponent[] }) {
  if (components.length === 0) {
    return <EmptyState title="No confidence components" message="The backend did not return component scoring for this signal." />;
  }

  return (
    <div className="space-y-3">
      {components.map((component, index) => (
        <AnimatedListItem
          as="section"
          key={component.id}
          className={`${motionCardClass} ${motionRevealPresetClass("scale-subtle")} muted-surface rounded-lg p-4`}
          style={motionRevealDensityStyle(index, "compact")}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-[var(--strong)]">{component.component_name}</h3>
            <span className="text-sm font-medium text-slate-500">{formatPercent(component.component_score)}</span>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{component.reason}</p>
          <p className="mt-2 text-xs text-slate-500">
            Weighted score {formatDecimal(component.weighted_score)} with weight {formatDecimal(component.component_weight)}
          </p>
        </AnimatedListItem>
      ))}
    </div>
  );
}
