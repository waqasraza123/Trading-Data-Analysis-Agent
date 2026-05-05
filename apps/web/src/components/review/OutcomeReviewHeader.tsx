import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import type { OutcomeReviewData } from "@/lib/review/types";

export function OutcomeReviewHeader({ data }: { data: OutcomeReviewData }) {
  return (
    <PageHeader
      eyebrow="Outcome and journal review"
      title="Daily learning loop"
      description="Review recently observed signal outcomes, connect notes, and inspect reliability diagnostics without broker execution or advice language."
      actions={
        <>
        <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
        <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "journal", "brief", "triage", "preferences"]} />
      </>
      }
    />
  );
}
