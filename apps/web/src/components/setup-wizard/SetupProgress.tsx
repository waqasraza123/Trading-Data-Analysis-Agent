import type { WorkspaceSetupRun, WorkspaceSetupStepKey } from "@/lib/setup-wizard/types";
import { setupStepOrder } from "@/lib/setup-wizard/validation";

const stepLabels: Record<WorkspaceSetupStepKey, string> = {
  workspace: "Workspace",
  user: "Operator",
  symbols: "Symbols",
  data_source: "Source",
  credential_reference: "Credential",
  watchlist: "Watchlist",
  scanner_preset: "Preset",
  preference_profile: "Preferences",
  demo_data: "Demo data",
  readiness_check: "Readiness",
  first_scan: "First scan",
};

export function SetupProgress({
  run,
  activeStep,
  onSelectStep,
}: {
  run: WorkspaceSetupRun | null;
  activeStep: WorkspaceSetupStepKey;
  onSelectStep: (step: WorkspaceSetupStepKey) => void;
}) {
  return (
    <div className="surface rounded-lg p-4">
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
        {setupStepOrder.map((step) => {
          const status =
            run?.step_results.find((result) => result.step_key === step)?.status || "pending";
          const active = step === activeStep;
          return (
            <button
              key={step}
              className={`rounded-md border px-3 py-2 text-left text-sm ${
                active
                  ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--strong)]"
                  : "border-[var(--line)] bg-[var(--panel)] text-slate-600 dark:text-slate-300"
              }`}
              type="button"
              onClick={() => onSelectStep(step)}
            >
              <span className="block font-semibold">{stepLabels[step]}</span>
              <span className="mt-1 block text-xs capitalize text-slate-500">
                {status.replaceAll("_", " ")}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
