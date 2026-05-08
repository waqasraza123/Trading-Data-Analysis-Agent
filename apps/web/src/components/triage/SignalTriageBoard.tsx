import { EmptyState } from "@/components/empty-states/empty-state";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { triageColumns } from "@/lib/triage/labels";
import type { TriageBoardData } from "@/lib/triage/types";
import { cn } from "@/lib/ui/cn";
import { motionRevealClass, motionRevealStyle } from "@/lib/ui/motion";
import { SignalTriageColumn } from "./SignalTriageColumn";
import { TriageEmptyState } from "./TriageEmptyState";
import { TriageErrorState } from "./TriageErrorState";
import { TriageFilters } from "./TriageFilters";
import { TriageSummary } from "./TriageSummary";

export function SignalTriageBoard({ data }: { data: TriageBoardData }) {
  return (
    <div className={cn("space-y-6", motionRevealClass())}>
      <div style={motionRevealStyle(0, 45)}>
        <PageHeader
          className={motionRevealClass()}
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
      </div>
      {!data.workspace ? (
        <div style={motionRevealStyle(1, 45)}>
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before workspace-scoped triage can load."
          />
        </div>
      ) : (
        <>
          <div style={motionRevealStyle(2, 45)}>
            <TriageSummary data={data} />
          </div>
          <div style={motionRevealStyle(3, 45)}>
            <TriageFilters data={data} />
          </div>
          <div style={motionRevealStyle(4, 45)}>
            <TriageErrorState failures={data.failures} />
          </div>
          {data.candidates.length === 0 ? (
            <div style={motionRevealStyle(5, 45)}>
              <TriageEmptyState />
            </div>
          ) : (
            <div className="overflow-x-auto pb-3" style={motionRevealStyle(6, 45)}>
              <div className="grid min-w-[1920px] grid-cols-6 gap-4">
                {triageColumns.map((column, index) => (
                  <SignalTriageColumn
                    key={column.key}
                    column={column}
                    candidates={data.candidates.filter((candidate) => candidate.classification.column === column.key)}
                    style={motionRevealStyle(index, 45)}
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
