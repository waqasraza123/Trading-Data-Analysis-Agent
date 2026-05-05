"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { runDailyRoutineTemplate } from "@/lib/api/dailyRoutines";
import { safeRoutineText } from "@/lib/routines/labels";
import type { UUID } from "@/lib/api/types";

type RoutineRunButtonProps = {
  templateId: UUID;
  workspaceId: UUID | null;
  watchlistId: UUID | null;
  preferenceProfileId: UUID | null;
};

export function RoutineRunButton({
  templateId,
  workspaceId,
  watchlistId,
  preferenceProfileId,
}: RoutineRunButtonProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function runRoutine() {
    if (!workspaceId) {
      setMessage("Workspace is required.");
      return;
    }
    setPending(true);
    setMessage(null);
    const result = await runDailyRoutineTemplate(templateId, {
      workspace_id: workspaceId,
      watchlist_id: watchlistId,
      preference_profile_id: preferenceProfileId,
      enable_notifications: false,
      allow_provider_polling: false,
      input_json: {
        source: "command_center",
        noBrokerExecution: true,
        noAutoTrading: true,
        noFinancialAdvice: true,
      },
    });
    setPending(false);
    if (!result.ok) {
      setMessage(result.error.message);
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    params.set("workspaceId", workspaceId);
    params.set("routineRunId", result.data.id);
    router.push(`/command-center?${params.toString()}`);
    router.refresh();
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <button
        className="rounded-md bg-[var(--accent)] px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        disabled={pending || !workspaceId}
        type="button"
        onClick={runRoutine}
      >
        {pending ? "Running routine" : "Run routine"}
      </button>
      {message && (
        <p className="text-xs leading-5 text-amber-700 dark:text-amber-200">
          {safeRoutineText(message)}
        </p>
      )}
    </div>
  );
}
