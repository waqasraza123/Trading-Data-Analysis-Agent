import { CommandCenterOverviewItemList } from "./CommandCenterWorkflowStatus";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export function CommandCenterAvoidConditions({ overview }: { overview: WorkspaceOverview }) {
  return <CommandCenterOverviewItemList title="Avoid Conditions" eyebrow="Review filters" items={overview.avoid_conditions} empty="No avoid conditions from overview." workspaceId={overview.workspace_id} />;
}
