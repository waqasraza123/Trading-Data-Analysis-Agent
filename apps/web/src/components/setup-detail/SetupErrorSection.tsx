import { Badge } from "@/components/status/badge";
import { AnimatedListItem, motionRevealDensityStyle } from "@/lib/ui/motion";
import type { SetupDetailFailure } from "@/lib/setup-detail/types";

type SetupErrorSectionProps = {
  failures: SetupDetailFailure[];
};

export function SetupErrorSection({ failures }: SetupErrorSectionProps) {
  if (failures.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {failures.map((failure, index) => (
        <AnimatedListItem
          as="div"
          key={`${failure.label}-${failure.status}-${failure.message}`}
          style={motionRevealDensityStyle(index, "compact")}
        >
          <div className="muted-surface rounded-lg p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={failure.label} tone={failure.missing ? "info" : "warning"} />
            <span className="text-xs font-medium text-slate-500">
              {failure.status > 0 ? `HTTP ${failure.status}` : "Network"}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{failure.message}</p>
        </div>
        </AnimatedListItem>
      ))}
    </div>
  );
}
