import { runWorkspaceQuickAction } from "@/lib/api/workspaceQuickActions";
import type { UUID } from "@/lib/api/types";
import type { WorkspaceQuickActionRequest } from "@/lib/command-center/overviewTypes";
import type { DailyWorkflowActionType } from "./types";

export function buildQuickActionRequest(
  actionType: DailyWorkflowActionType,
  input: {
    watchlistId?: UUID | null;
    preferenceProfileId?: UUID | null;
    options?: WorkspaceQuickActionRequest["options"];
  } = {},
): WorkspaceQuickActionRequest {
  return {
    action_type: actionType,
    watchlist_id: input.watchlistId || null,
    preference_profile_id: input.preferenceProfileId || null,
    options: input.options || {},
  };
}

export async function runDailyWorkflowQuickAction(
  workspaceId: UUID,
  actionType: DailyWorkflowActionType,
  input: {
    watchlistId?: UUID | null;
    preferenceProfileId?: UUID | null;
    options?: WorkspaceQuickActionRequest["options"];
  } = {},
) {
  return runWorkspaceQuickAction(workspaceId, buildQuickActionRequest(actionType, input));
}
