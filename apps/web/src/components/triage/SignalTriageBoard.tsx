import { EmptyState } from "@/components/empty-states/empty-state";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { triageColumns } from "@/lib/triage/labels";
import type { TriageBoardData } from "@/lib/triage/types";
import { SignalTriageColumn } from "./SignalTriageColumn";
import { TriageEmptyState } from "./TriageEmptyState";
import { TriageErrorState } from "./TriageErrorState";
import { TriageFilters } from "./TriageFilters";
import { TriageSummary } from "./TriageSummary";

export function SignalTriageBoard({ data }: { data: TriageBoardData }) {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Premium review workflow"
        title="Setup triage"
        description="Review stored deterministic setups by priority, freshness, evidence quality, unresolved context, and observed behavior."
        actions={
          <>
          <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
          <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "brief", "scanner", "dataOnboarding", "preferences", "review"]} />
        </>
        }
      />
      {!data.workspace ? (
        <EmptyState
          title="No workspace available"
          message="Seed or create a workspace in the API before workspace-scoped triage can load."
        />
      ) : (
        <>
          <TriageSummary data={data} />
          <TriageFilters data={data} />
          <TriageErrorState failures={data.failures} />
          {data.candidates.length === 0 ? (
            <TriageEmptyState />
          ) : (
            <div className="overflow-x-auto pb-3">
              <div className="grid min-w-[1920px] grid-cols-6 gap-4">
              {triageColumns.map((column) => (
                <SignalTriageColumn
                  key={column.key}
                  column={column}
                  candidates={data.candidates.filter((candidate) => candidate.classification.column === column.key)}
                />
              ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
