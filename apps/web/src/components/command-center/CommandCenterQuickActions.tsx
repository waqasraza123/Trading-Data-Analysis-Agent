"use client";

import { useState } from "react";
import Link from "next/link";
import { commandCenterHref } from "@/lib/command-center/labels";
import { dailyWorkflowActionLabel } from "@/lib/daily-workflow/safeLabels";
import type { DailyWorkflowActionType } from "@/lib/daily-workflow/types";
import { runDailyWorkflowQuickAction } from "@/lib/daily-workflow/quickActions";
import { AnimatedListItem, MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealDensityStyle, motionRevealPresetClass } from "@/lib/ui/motion";
import type { UUID } from "@/lib/api/types";

type CommandCenterQuickActionsProps = {
  workspaceId: UUID | null;
  watchlistId: UUID | null;
  preferenceProfileId: UUID | null;
};

const actions: DailyWorkflowActionType[] = [
  "run_product_readiness",
  "refresh_provider_health",
  "run_daily_workflow",
  "generate_daily_brief",
  "score_recent_signals",
  "refresh_market_memory",
];

export function CommandCenterQuickActions({
  workspaceId,
  watchlistId,
  preferenceProfileId,
}: CommandCenterQuickActionsProps) {
  const actionPillClassName =
    "rounded-full border px-4 py-2 text-sm font-semibold transition";
  const [pendingAction, setPendingAction] = useState<DailyWorkflowActionType | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runAction(actionType: DailyWorkflowActionType) {
    if (!workspaceId || pendingAction) {
      return;
    }
    setPendingAction(actionType);
    setMessage(null);
    setError(null);
    const result = await runDailyWorkflowQuickAction(workspaceId, actionType, {
      watchlistId,
      preferenceProfileId,
      options: actionType === "run_daily_workflow" ? { allowProviderPolling: false } : {},
    });
    if (result.ok) {
      setMessage(result.data.summary);
    } else if (result.error.status === 403) {
      setError("Action not available for this workspace/user.");
    } else {
      setError(result.error.message || "Backend action unavailable.");
    }
    setPendingAction(null);
  }

  return (
    <div className={`rounded-2xl border border-slate-200 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-950/55 ${motionRevealPresetClass()}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">Backend-safe daily actions</p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Explicit deterministic tasks only.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <AnimatedListItem as="div" style={motionRevealDensityStyle(0, "compact")}>
            <Link
              href={commandCenterHref("/scanner", workspaceId)}
              className={`${actionPillClassName} ${MOTION_INTERACTIVE_CLASS} ${motionCardClass} border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-100`}
            >
              Open scanner
            </Link>
          </AnimatedListItem>
          <AnimatedListItem as="div" style={motionRevealDensityStyle(1, "compact")}>
            <Link
              href={commandCenterHref("/data/onboarding", workspaceId)}
              className={`${actionPillClassName} ${MOTION_INTERACTIVE_CLASS} ${motionCardClass} border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100`}
            >
              Open data onboarding
            </Link>
          </AnimatedListItem>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <AnimatedListItem as="div" style={motionRevealDensityStyle(2, "compact")}>
          <Link
            href={commandCenterHref("/command-center", workspaceId)}
            className={`${actionPillClassName} ${MOTION_INTERACTIVE_CLASS} ${motionCardClass} border-slate-200 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200`}
          >
            Refresh status
          </Link>
        </AnimatedListItem>
        {actions.map((actionType, index) => (
          <AnimatedListItem key={actionType} as="div" style={motionRevealDensityStyle(index + 3, "compact")}>
            <button
              type="button"
              disabled={!workspaceId || pendingAction !== null}
              onClick={() => void runAction(actionType)}
              className={`${actionPillClassName} ${MOTION_INTERACTIVE_CLASS} ${motionCardClass} border-sky-200 bg-sky-50 text-sky-800 disabled:cursor-not-allowed disabled:opacity-50 dark:border-sky-900 dark:bg-sky-950 dark:text-sky-100`}
            >
              {pendingAction === actionType ? "Running..." : dailyWorkflowActionLabel(actionType)}
            </button>
          </AnimatedListItem>
        ))}
      </div>
      {message && <p className="mt-3 text-sm text-emerald-700 dark:text-emerald-300">{message}</p>}
      {error && <p className="mt-3 text-sm text-rose-700 dark:text-rose-300">{error}</p>}
    </div>
  );
}
