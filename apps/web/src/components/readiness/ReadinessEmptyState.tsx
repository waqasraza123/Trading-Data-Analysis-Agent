import { Panel } from "@/components/layout/panel";
import { ReadinessRunButton } from "./ReadinessRunButton";

export function ReadinessEmptyState({ workspaceId }: { workspaceId?: string | null }) {
  return (
    <Panel title="No readiness run yet" eyebrow="Setup validation">
      <div className="muted-surface rounded-lg p-5">
        <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
          Run the checklist explicitly to validate API, database, seed data, workspace setup, data freshness, scanner readiness, workers, optional notifications, and journal availability.
        </p>
        <div className="mt-4">
          <ReadinessRunButton workspaceId={workspaceId || null} />
        </div>
      </div>
    </Panel>
  );
}
