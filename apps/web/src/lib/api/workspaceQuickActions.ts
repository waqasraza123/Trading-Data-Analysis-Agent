import { apiPost } from "./client";
import type { ApiResult, UUID } from "./types";
import type {
  WorkspaceQuickActionRequest,
  WorkspaceQuickActionResponse,
} from "@/lib/command-center/overviewTypes";

export function runWorkspaceQuickAction(
  workspaceId: UUID,
  request: WorkspaceQuickActionRequest,
): Promise<ApiResult<WorkspaceQuickActionResponse>> {
  return apiPost<WorkspaceQuickActionResponse>(`/workspaces/${workspaceId}/quick-actions`, request, {
    timeoutMs: 30000,
  });
}
