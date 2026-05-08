import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import {
  AnimatedListItem,
  motionCardClass,
  motionRevealDensityStyle,
  motionRevealPresetClass,
} from "@/lib/ui/motion";
import type { CommandCenterFailure } from "@/lib/command-center/types";

export function CommandCenterErrorState({
  failures,
  backendUnavailable,
}: {
  failures: CommandCenterFailure[];
  backendUnavailable: boolean;
}) {
  const visibleFailures = failures.filter((failure) => !failure.missing).slice(0, 8);
  if (!backendUnavailable && visibleFailures.length === 0) {
    return null;
  }
  return (
    <Panel title="Backend state" eyebrow="Availability" className={motionRevealPresetClass()}>
      {backendUnavailable && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
          Backend unavailable. The command center is showing safe empty states where data could not be loaded.
        </div>
      )}
      {visibleFailures.length > 0 ? (
        <div className="space-y-2">
          {visibleFailures.map((failure, index) => (
            <AnimatedListItem
              key={`${failure.label}:${failure.status}:${failure.message}`}
              as="article"
              preset="scale-subtle"
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div
                className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--line)] p-3 ${motionCardClass}`}
              >
                <div>
                  <p className="text-sm font-semibold text-[var(--strong)]">{failure.label}</p>
                  <p className="text-sm text-slate-500">{failure.message}</p>
                </div>
                <Badge
                  value={failure.status === 0 ? "Network" : String(failure.status)}
                  tone={failure.status === 0 ? "danger" : "warning"}
                />
              </div>
            </AnimatedListItem>
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No section-level backend failures were reported.</p>
      )}
    </Panel>
  );
}
