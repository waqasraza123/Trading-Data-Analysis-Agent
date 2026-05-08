import { Badge } from "@/components/status/badge";
import { cn } from "@/lib/ui/cn";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { DemoModeFlowStep } from "@/lib/demo-mode/types";

export function DemoFlowSteps({ steps }: { steps: DemoModeFlowStep[] }) {
  if (steps.length === 0) {
    return null;
  }
  return (
    <div className="grid gap-3">
      {steps.map((step, index) => (
        <AnimatedListItem
          as="article"
          key={step.key}
          className={cn(
            "muted-surface rounded-lg p-4",
            motionCardClass,
            motionRevealPresetClass("scale-subtle"),
          )}
          style={motionRevealDensityStyle(index, "compact")}
        >
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-[var(--strong)]">{step.key.replaceAll("_", " ")}</p>
              <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{step.summary}</p>
            </div>
            <Badge value={step.status} tone={step.status === "completed" ? "good" : "warning"} />
          </div>
        </AnimatedListItem>
      ))}
    </div>
  );
}
