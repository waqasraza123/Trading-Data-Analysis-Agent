import { CommandCenterOverviewItemList } from "./CommandCenterWorkflowStatus";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export function CommandCenterNeedsConfirmation({ overview }: { overview: WorkspaceOverview }) {
  return <CommandCenterOverviewItemList title="Needs Confirmation" eyebrow="Pending context" items={overview.needs_confirmation} empty="No confirmation queue from overview." workspaceId={overview.workspace_id} />;
}
