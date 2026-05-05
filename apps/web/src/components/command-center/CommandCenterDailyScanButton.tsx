"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { runDailyWorkflow } from "@/lib/api/dailyWorkflows";
import { safeWorkflowText } from "@/lib/daily-workflows/labels";
import type { UUID } from "@/lib/api/types";

type CommandCenterDailyScanButtonProps = {
  workspaceId: UUID | null;
  watchlistId: UUID | null;
  preferenceProfileId?: UUID | null;
  className?: string;
};

export function CommandCenterDailyScanButton({
  workspaceId,
  watchlistId,
  preferenceProfileId = null,
  className = "",
}: CommandCenterDailyScanButtonProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runScan() {
    if (!workspaceId) {
      setMessage("Workspace required");
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await runDailyWorkflow({
      workspace_id: workspaceId,
      workflow_type: watchlistId ? "watchlist_scan" : "daily_scan",
      watchlist_id: watchlistId || undefined,
      preference_profile_id: preferenceProfileId || null,
      options: {
        prepare_gap_recovery: true,
        allow_provider_polling: false,
        run_scan: true,
        generate_setup_context: true,
        score_priorities: true,
        generate_digest: true,
        generate_brief: true,
      },
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    params.set("workspaceId", workspaceId);
    params.set("workflowRunId", result.data.id);
    router.push(`/command-center?${params.toString()}`);
    router.refresh();
  }

  return (
    <div className={className}>
      <button
        className="inline-flex min-h-11 items-center justify-center rounded-full border border-teal-500 bg-teal-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-teal-950/10 transition hover:-translate-y-0.5 hover:bg-teal-600 disabled:cursor-not-allowed disabled:opacity-60 dark:border-teal-400 dark:bg-teal-400 dark:text-slate-950 dark:hover:bg-teal-300"
        disabled={pending || !workspaceId}
        type="button"
        onClick={runScan}
      >
        {pending ? "Scan running" : "Run deterministic daily scan"}
      </button>
      {message && <p className="mt-2 text-xs font-medium text-amber-700 dark:text-amber-200">{safeWorkflowText(message)}</p>}
    </div>
  );
}
