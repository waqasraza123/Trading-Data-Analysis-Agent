import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { routineLabel } from "@/lib/routines/labels";
import type { UUID } from "@/lib/api/types";
import type {
  DailyRoutineFailure,
  DailyRoutineRun,
  DailyRoutineRunStep,
  DailyRoutineTemplate,
} from "@/lib/routines/types";
import { RoutineRunButton } from "./RoutineRunButton";
import { RoutineRunStatus } from "./RoutineRunStatus";

type RoutineTemplateListProps = {
  workspaceId: UUID | null;
  watchlistId: UUID | null;
  preferenceProfileId: UUID | null;
  templates: DailyRoutineTemplate[];
  runs: DailyRoutineRun[];
  latestRun: DailyRoutineRun | null;
  latestRunSteps: DailyRoutineRunStep[];
  failures: DailyRoutineFailure[];
};

export function RoutineTemplateList({
  workspaceId,
  watchlistId,
  preferenceProfileId,
  templates,
  runs,
  latestRun,
  latestRunSteps,
  failures,
}: RoutineTemplateListProps) {
  const latestByTemplate = new Map(runs.map((run) => [run.template_id, run]));
  return (
    <Panel title="Daily routines" eyebrow="Template runner">
      {failures.length > 0 && (
        <div className="mb-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:bg-amber-950 dark:text-amber-100">
          Routine data is partially unavailable.
        </div>
      )}
      {templates.length === 0 ? (
        <div className="muted-surface rounded-lg p-5 text-sm leading-6 text-slate-500">
          No routine templates are active.
        </div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(340px,0.8fr)]">
          <div className="grid gap-3">
            {templates.slice(0, 9).map((template) => {
              const latest = latestByTemplate.get(template.id);
              return (
                <div key={template.id} className="muted-surface rounded-lg p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-semibold text-[var(--strong)]">{template.name}</h3>
                        <Badge value={routineLabel(template.routine_type)} tone="neutral" />
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                        {template.description}
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        {template.steps_json.length} bounded steps
                        {latest ? ` · latest ${routineLabel(latest.status)}` : ""}
                      </p>
                    </div>
                    <RoutineRunButton
                      templateId={template.id}
                      workspaceId={workspaceId}
                      watchlistId={watchlistId}
                      preferenceProfileId={preferenceProfileId}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <RoutineRunStatus run={latestRun} steps={latestRunSteps} />
        </div>
      )}
    </Panel>
  );
}
