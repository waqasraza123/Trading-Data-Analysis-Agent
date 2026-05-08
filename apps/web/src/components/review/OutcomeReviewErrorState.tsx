import { Panel } from "@/components/layout/panel";
import { cn } from "@/lib/ui/cn";
import { motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { OutcomeReviewFailure } from "@/lib/review/types";

export function OutcomeReviewErrorState({ failures }: { failures: OutcomeReviewFailure[] }) {
  const visibleFailures = failures.filter((failure) => !failure.missing).slice(0, 5);
  if (visibleFailures.length === 0) {
    return null;
  }
  return (
    <Panel title="Backend warnings" eyebrow="Scoped failures">
      <div className="space-y-2">
        {visibleFailures.map((failure, index) => (
          <div
            key={`${failure.label}-${failure.status}-${failure.message}`}
            className={cn(
              "rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-950 dark:text-amber-100",
              motionCardClass,
              motionRevealPresetClass(),
            )}
            style={motionRevealDensityStyle(index, "compact")}
          >
            <span className="font-semibold">{failure.label}:</span> {failure.message}
          </div>
        ))}
      </div>
    </Panel>
  );
}
