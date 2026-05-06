import Link from "next/link";
import { onboardingStepStateLabel, onboardingTone, safeOnboardingCopy } from "@/lib/onboarding/labels";
import { withWorkspace } from "@/lib/onboarding/nextStep";
import type { OnboardingActionType, OnboardingStep } from "@/lib/onboarding/types";

export function OnboardingStepCard({
  step,
  workspaceId,
  pending,
  disabled,
  onAction,
}: {
  step: OnboardingStep;
  workspaceId?: string | null;
  pending?: boolean;
  disabled?: boolean;
  onAction: (actionType: OnboardingActionType) => void;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-muted)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-[var(--strong)]">{step.title}</p>
            <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${onboardingTone(step.state)}`}>
              {onboardingStepStateLabel(step.state)}
            </span>
          </div>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
            {safeOnboardingCopy(step.description)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {step.action_type && step.state !== "complete" && (
            <button
              type="button"
              className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              disabled={pending || disabled}
              onClick={() => onAction(step.action_type as OnboardingActionType)}
            >
              {pending ? "Working" : "Run action"}
            </button>
          )}
          <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={withWorkspace(step.route, workspaceId)}>
            Open
          </Link>
        </div>
      </div>
    </div>
  );
}
