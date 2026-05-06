import { CommandCenterOverviewItemList } from "./CommandCenterWorkflowStatus";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export function CommandCenterOutcomeUpdates({ overview }: { overview: WorkspaceOverview }) {
  return <CommandCenterOverviewItemList title="Outcome Updates" eyebrow="Observed horizons" items={overview.outcome_updates} empty="No outcome updates from overview." workspaceId={overview.workspace_id} />;
}
