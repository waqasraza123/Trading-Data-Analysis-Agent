import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Badge } from "@/components/status/badge";
import { PageHeader } from "@/components/ui/PageHeader";
import type { ScannerData } from "@/lib/scanner/types";

export function ScannerHeader({ data }: { data: ScannerData }) {
  return (
    <PageHeader
      eyebrow="Scanner controls"
      title="Watchlist scanner"
      description="Configure backend deterministic scans for watchlists and single symbols. This surface starts analysis runs only and does not execute orders or send messages."
      actions={
        <>
        <Badge value={data.workspace?.name || "No workspace"} tone={data.workspace ? "info" : "warning"} />
        <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "brief", "triage", "dataOnboarding", "preferences", "review", "journal"]} />
      </>
      }
    />
  );
}
