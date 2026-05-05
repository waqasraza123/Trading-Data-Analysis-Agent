import { WorkflowLinks } from "@/components/layout/workflow-links";
import { PageHeader } from "@/components/ui/PageHeader";
import { Tabs } from "@/components/ui/Tabs";
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
      <PageHeader
        eyebrow="Data onboarding"
        title="Live data readiness"
        description="Configure source coverage and verify current final-candle readiness before deterministic analysis."
        actions={
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
        }
      />
      <div className="surface rounded-lg p-4">
        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <div>
            <p className="font-medium text-[var(--strong)]">{workspace?.name || "Workspace not selected"}</p>
            <p className="mt-1 text-slate-500">{apiBaseUrl}</p>
          </div>
          <Tabs
            onSelect={(key) => onStepChange(key as OnboardingStepKey)}
            items={steps.map((step, index) => ({
              key: step.key,
              label: `${index + 1}. ${step.label}`,
              active: step.key === activeStep,
            }))}
          />
        </div>
      </div>
    </section>
  );
}
