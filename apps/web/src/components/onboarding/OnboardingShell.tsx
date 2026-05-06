"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { runOnboardingAction } from "@/lib/api/onboarding";
import { onboardingReadinessLabel, safeOnboardingCopy } from "@/lib/onboarding/labels";
import { isCommandCenterReady, withWorkspace } from "@/lib/onboarding/nextStep";
import type {
  OnboardingActionType,
  OnboardingPageData,
  OnboardingStatusResponse,
} from "@/lib/onboarding/types";
import { OnboardingCompletionPanel } from "./OnboardingCompletionPanel";
import { OnboardingErrorState } from "./OnboardingErrorState";
import { OnboardingHeader } from "./OnboardingHeader";
import { OnboardingNextStepPanel } from "./OnboardingNextStepPanel";
import { OnboardingStepList } from "./OnboardingStepList";
import { ReadinessScorePanel } from "./ReadinessScorePanel";
import { DemoWorkspaceCard } from "./DemoWorkspaceCard";

export function OnboardingShell({ initialData }: { initialData: OnboardingPageData }) {
  const [status, setStatus] = useState<OnboardingStatusResponse | null>(initialData.status);
  const [pendingAction, setPendingAction] = useState<OnboardingActionType | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(initialData.statusError?.message || null);
  const workspaceId = status?.workspace.workspace_id || initialData.selectedWorkspaceId || null;

  const availableActions = useMemo(
    () => new Set(status?.steps.flatMap((step) => (step.action_type ? [step.action_type] : [])) || []),
    [status],
  );

  async function runAction(actionType: OnboardingActionType) {
    setPendingAction(actionType);
    setError(null);
    setMessage(null);
    const result = await runOnboardingAction({
      actionType,
      workspaceId,
      userId: status?.user.user_id || null,
    });
    if (!result.ok) {
      setError(result.error.message);
      setPendingAction(null);
      return;
    }
    setStatus(result.data.onboarding_status || status);
    setMessage(result.data.message);
    setPendingAction(null);
  }

  return (
    <div className="space-y-6">
      <OnboardingHeader
        title="First-run onboarding"
        description="Review setup context, close readiness gaps, and open the command center when the workspace is ready for deterministic analysis."
        label={status ? onboardingReadinessLabel(status.status.readiness_label) : "Backend unavailable"}
      />
      {error && <OnboardingErrorState message={error} />}
      {message && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-900">
          {safeOnboardingCopy(message)}
        </div>
      )}
      {status ? (
        <>
          <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_420px]">
            <div className="space-y-5">
              <ReadinessScorePanel status={status} />
              <OnboardingNextStepPanel
                status={status}
                pendingAction={pendingAction}
                onAction={runAction}
              />
              <OnboardingStepList
                status={status}
                pendingAction={pendingAction}
                availableActions={availableActions}
                onAction={runAction}
              />
            </div>
            <div className="space-y-5">
              <DemoWorkspaceCard
                status={status}
                pending={pendingAction === "run_demo_flow"}
                onAction={() => runAction("run_demo_flow")}
              />
              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-5">
                <p className="text-sm font-semibold text-[var(--strong)]">Daily workflow links</p>
                <div className="mt-4 grid gap-2">
                  <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={withWorkspace("/data/onboarding", workspaceId)}>
                    Data onboarding
                  </Link>
                  <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={withWorkspace("/scanner", workspaceId)}>
                    Scanner
                  </Link>
                  <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={withWorkspace("/preferences/strategy", workspaceId)}>
                    Review preferences
                  </Link>
                  <Link className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-semibold" href={withWorkspace("/readiness", workspaceId)}>
                    Product readiness
                  </Link>
                  <Link className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white" href={withWorkspace("/command-center", workspaceId)}>
                    Command center
                  </Link>
                </div>
              </div>
            </div>
          </section>
          {isCommandCenterReady(status) && <OnboardingCompletionPanel workspaceId={workspaceId} />}
        </>
      ) : (
        <OnboardingErrorState message="The onboarding status endpoint is unavailable. The existing setup wizard remains available." />
      )}
    </div>
  );
}
