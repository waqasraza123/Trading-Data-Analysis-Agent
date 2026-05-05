import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import { routineLabel, routineStatusTone, safeRoutineText } from "@/lib/routines/labels";
import type { DailyRoutineRun, DailyRoutineRunStep } from "@/lib/routines/types";

type RoutineRunStatusProps = {
  run: DailyRoutineRun | null;
  steps: DailyRoutineRunStep[];
};

export function RoutineRunStatus({ run, steps }: RoutineRunStatusProps) {
  if (!run) {
    return (
      <div className="muted-surface rounded-lg p-4 text-sm leading-6 text-slate-500">
        No routine run has been recorded for this workspace.
      </div>
    );
  }
  const visibleSteps = steps.length > 0 ? steps : stepsFromRun(run);
  return (
    <div className="space-y-3">
      <div className="muted-surface rounded-lg p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="font-semibold text-[var(--strong)]">Routine {run.id.slice(0, 8)}</h3>
            <p className="mt-1 text-sm text-slate-500">
              Started {formatDateTime(run.started_at)} · Completed {formatDateTime(run.completed_at)}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {safeRoutineText(run.summary)}
            </p>
          </div>
          <Badge value={run.status} tone={routineStatusTone(run.status)} />
        </div>
        {run.error_message && (
          <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-100">
            {safeRoutineText(run.error_message)}
          </p>
        )}
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {visibleSteps.slice(0, 8).map((step) => (
          <div key={step.id} className="muted-surface flex items-center justify-between gap-3 rounded-lg p-3">
            <div>
              <p className="text-sm font-semibold text-[var(--strong)]">
                {routineLabel(step.step_key)}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {safeRoutineText(step.skipped_reason || step.error_message, "Step result recorded")}
              </p>
            </div>
            <Badge value={step.status} tone={routineStatusTone(step.status)} />
          </div>
        ))}
      </div>
    </div>
  );
}

function stepsFromRun(run: DailyRoutineRun): DailyRoutineRunStep[] {
  return run.step_results_json.map((step, index) => ({
    id: String(step.id || `${run.id}-${index}`),
    workspace_id: run.workspace_id,
    routine_run_id: run.id,
    step_key: String(step.stepKey || step.step_key || "routine_step"),
    status: String(step.status || "pending") as DailyRoutineRunStep["status"],
    input_json: {},
    output_json: null,
    skipped_reason: typeof step.skippedReason === "string" ? step.skippedReason : null,
    error_message: typeof step.errorMessage === "string" ? step.errorMessage : null,
    started_at: typeof step.startedAt === "string" ? step.startedAt : null,
    completed_at: typeof step.completedAt === "string" ? step.completedAt : null,
    created_at: run.created_at,
    updated_at: run.updated_at,
  }));
}
