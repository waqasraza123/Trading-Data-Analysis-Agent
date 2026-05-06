import { CommandCenterOverviewItemList } from "./CommandCenterWorkflowStatus";
import type { WorkspaceOverview } from "@/lib/command-center/overviewTypes";

export function CommandCenterReviewFirst({ overview }: { overview: WorkspaceOverview }) {
  return <CommandCenterOverviewItemList title="Review First" eyebrow="Priority from overview" items={overview.review_first} empty="No review-first items from overview." workspaceId={overview.workspace_id} />;
}
