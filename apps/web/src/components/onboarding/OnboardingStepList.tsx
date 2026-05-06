import type { OnboardingActionType, OnboardingStatusResponse } from "@/lib/onboarding/types";
import { OnboardingStepCard } from "./OnboardingStepCard";

export function OnboardingStepList({
  status,
  pendingAction,
  availableActions,
  onAction,
}: {
  status: OnboardingStatusResponse;
  pendingAction: OnboardingActionType | null;
  availableActions: Set<OnboardingActionType>;
  onAction: (actionType: OnboardingActionType) => void;
}) {
  return (
    <section className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--strong)]">Setup path</p>
          <p className="mt-1 text-sm text-slate-500">Complete these steps in order for daily analysis.</p>
        </div>
      </div>
      <div className="mt-4 grid gap-3">
        {status.steps
          .filter((step) => step.key !== "demo_mode")
          .map((step) => (
            <OnboardingStepCard
              key={step.key}
              step={step}
              disabled={Boolean(step.action_type && !availableActions.has(step.action_type))}
              pending={pendingAction === step.action_type}
              workspaceId={status.workspace.workspace_id}
              onAction={onAction}
            />
          ))}
      </div>
    </section>
  );
}
