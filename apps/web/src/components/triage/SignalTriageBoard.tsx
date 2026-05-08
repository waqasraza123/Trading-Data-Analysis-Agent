import { EmptyState } from "@/components/empty-states/empty-state";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { triageColumns } from "@/lib/triage/labels";
import type { TriageBoardData } from "@/lib/triage/types";
import { cn } from "@/lib/ui/cn";
import { motionRevealClass, motionRevealDensityStyle } from "@/lib/ui/motion";
import { SignalTriageColumn } from "./SignalTriageColumn";
import { TriageEmptyState } from "./TriageEmptyState";
import { TriageErrorState } from "./TriageErrorState";
import { TriageFilters } from "./TriageFilters";
import { TriageSummary } from "./TriageSummary";

export function SignalTriageBoard({ data }: { data: TriageBoardData }) {
  return (
    <div className={cn("space-y-6", motionRevealClass())}>
      <div style={motionRevealDensityStyle(0)}>
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
        <div style={motionRevealDensityStyle(1)}>
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before workspace-scoped triage can load."
          />
        </div>
      ) : (
        <>
          <div style={motionRevealDensityStyle(2)}>
            <TriageSummary data={data} />
          </div>
          <div style={motionRevealDensityStyle(3)}>
            <TriageFilters data={data} />
          </div>
          <div style={motionRevealDensityStyle(4)}>
            <TriageErrorState failures={data.failures} />
          </div>
          {data.candidates.length === 0 ? (
            <div style={motionRevealDensityStyle(5)}>
              <TriageEmptyState />
            </div>
          ) : (
            <div className="overflow-x-auto pb-3" style={motionRevealDensityStyle(6)}>
              <div className="grid min-w-[1920px] grid-cols-6 gap-4">
                {triageColumns.map((column, index) => (
                  <SignalTriageColumn
                    key={column.key}
                    column={column}
                    candidates={data.candidates.filter((candidate) => candidate.classification.column === column.key)}
                    style={motionRevealDensityStyle(index, "compact")}
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
