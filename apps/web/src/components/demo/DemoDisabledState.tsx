import { Panel } from "@/components/layout/panel";
import { motionCardClass, motionRevealPresetClass } from "@/lib/ui/motion";
import type { DemoModeStatus } from "@/lib/demo-mode/types";

export function DemoDisabledState({ status }: { status: DemoModeStatus | null }) {
  return (
    <Panel title="Demo mode disabled" eyebrow="Configuration" className={motionCardClass + " " + motionRevealPresetClass("scale-subtle")}>
      <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
        {status?.reason || "The backend demo-mode endpoint is unavailable. Enable demo mode in the API before running the product smoke flow."}
      </p>
      <div className="mt-4 muted-surface rounded-lg p-4 text-sm text-slate-600 dark:text-slate-300">
        Set <span className="font-mono">DEMO_MODE_ENABLED=true</span> or run with <span className="font-mono">APP_ENV=development</span>.
      </div>
    </Panel>
  );
}
