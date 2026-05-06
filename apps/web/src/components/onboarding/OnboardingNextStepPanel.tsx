import Link from "next/link";
import { safeOnboardingCopy } from "@/lib/onboarding/labels";
import { withWorkspace } from "@/lib/onboarding/nextStep";
import type { OnboardingActionType, OnboardingStatusResponse } from "@/lib/onboarding/types";

export function OnboardingNextStepPanel({
  status,
  pendingAction,
  onAction,
}: {
  status: OnboardingStatusResponse;
  pendingAction: OnboardingActionType | null;
  onAction: (actionType: OnboardingActionType) => void;
}) {
  const next = status.next_step;
  return (
    <section className="rounded-lg border border-sky-200 bg-sky-50 p-5 text-sky-950">
      <p className="text-sm font-semibold uppercase tracking-[0.12em]">Next step</p>
      <h2 className="mt-2 text-xl font-semibold">{safeOnboardingCopy(next.title)}</h2>
      <p className="mt-2 text-sm leading-6">{safeOnboardingCopy(next.description)}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {next.action_type && (
          <button
            type="button"
            className="rounded-md bg-sky-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            disabled={pendingAction !== null}
            onClick={() => onAction(next.action_type as OnboardingActionType)}
          >
            {pendingAction === next.action_type ? "Working" : "Complete next step"}
          </button>
        )}
        <Link className="rounded-md border border-sky-300 px-4 py-2 text-sm font-semibold" href={withWorkspace(next.route, status.workspace.workspace_id)}>
          Open route
        </Link>
      </div>
    </section>
  );
}
