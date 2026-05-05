import { Badge } from "@/components/status/badge";
import { ButtonLink } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import type { WorkspaceBrief } from "@/lib/brief/types";
import { formatDateTime } from "@/lib/formatting/dates";

export function BriefHeader({ brief }: { brief: WorkspaceBrief }) {
  return (
    <PageHeader
      eyebrow="Workspace brief"
      title="What to review now"
      description="Deterministic morning and intraday context across symbol state, setup context, outcomes, backend actions, and review queues."
      meta={
        <>
          <Badge value={brief.workspace?.name || "No workspace"} tone="info" />
          <Badge value={`Generated ${formatDateTime(brief.generatedAt)}`} />
        </>
      }
      actions={
        <>
        <ButtonLink href="/dashboard">
          Dashboard
        </ButtonLink>
        {brief.workspace && (
          <ButtonLink href={`/dashboard?workspaceId=${brief.workspace.id}`}>
            Workspace dashboard
          </ButtonLink>
        )}
        <WorkflowLinks workspaceId={brief.workspace?.id} targets={["commandCenter", "triage", "scanner", "dataOnboarding", "preferences", "review", "journal"]} />
      </>
      }
    />
  );
}
