import { CommandCenterOverviewItemList } from "./CommandCenterWorkflowStatus";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export function CommandCenterQualityWarnings({ overview }: { overview: WorkspaceOverview }) {
  return <CommandCenterOverviewItemList title="Quality Warnings" eyebrow="Data diagnostics" items={overview.quality_warnings} empty="No quality warnings from overview." workspaceId={overview.workspace_id} />;
}
