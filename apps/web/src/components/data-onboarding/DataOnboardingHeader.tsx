import { WorkflowLinks } from "@/components/layout/workflow-links";
import type { Workspace } from "@/lib/api/types";
import type { OnboardingSelection, OnboardingStepKey } from "@/lib/data-onboarding/types";

type DataOnboardingHeaderProps = {
  apiBaseUrl: string;
  workspace: Workspace | null;
  workspaces: Workspace[];
  selection: OnboardingSelection;
  steps: Array<{ key: OnboardingStepKey; label: string }>;
  activeStep: OnboardingStepKey;
  onStepChange: (step: OnboardingStepKey) => void;
  onWorkspaceChange: (workspaceId: string) => void;
};

export function DataOnboardingHeader({
  apiBaseUrl,
  workspace,
  workspaces,
  selection,
  steps,
  activeStep,
  onStepChange,
  onWorkspaceChange,
}: DataOnboardingHeaderProps) {
  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Data onboarding</p>
          <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">Live data readiness</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
            Configure source coverage and verify current final-candle readiness before deterministic analysis.
          </p>
        </div>
        <div className="grid gap-3">
          <div className="grid gap-2">
            <label className="text-xs font-semibold uppercase text-slate-500" htmlFor="workspace-select">
              Workspace
            </label>
            <select
              id="workspace-select"
              value={selection.workspaceId || ""}
              onChange={(event) => onWorkspaceChange(event.target.value)}
              className="min-w-60 rounded-md border border-[var(--line)] bg-[var(--panel)] px-3 py-2 text-sm"
            >
              {workspaces.map((candidate) => (
                <option key={candidate.id} value={candidate.id}>
                  {candidate.name}
                </option>
              ))}
            </select>
          </div>
          <WorkflowLinks workspaceId={selection.workspaceId} targets={["commandCenter", "brief", "triage", "scanner", "preferences", "review"]} />
        </div>
      </div>
      <div className="surface rounded-lg p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div>
            <p className="font-medium text-[var(--strong)]">{workspace?.name || "Workspace not selected"}</p>
            <p className="mt-1 text-slate-500">{apiBaseUrl}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {steps.map((step, index) => (
              <button
                key={step.key}
                type="button"
                onClick={() => onStepChange(step.key)}
                className={`rounded-md border px-3 py-2 text-xs font-semibold ${
                  step.key === activeStep
                    ? "border-teal-300 bg-teal-50 text-teal-800 dark:border-teal-800 dark:bg-teal-950 dark:text-teal-100"
                    : "border-[var(--line)] bg-[var(--panel)] text-slate-600 dark:text-slate-300"
                }`}
              >
                {index + 1}. {step.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
