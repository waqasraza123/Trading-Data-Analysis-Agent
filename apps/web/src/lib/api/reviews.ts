import { apiGet } from "./client";
import type { ApiResult, JsonRecord, UUID } from "./types";

export type OperatorReviewItem = {
  id: UUID;
  workspace_id: UUID;
  source_type: string;
  source_id: UUID;
  related_analysis_run_id: UUID | null;
  related_signal_id: UUID | null;
  related_reasoning_run_id: UUID | null;
  related_action_item_id: UUID | null;
  review_type: string;
  priority: string;
  status: string;
  title: string;
  summary: string;
  reason_code: string | null;
  evidence_json: JsonRecord;
  assigned_to_user_id: UUID | null;
  resolution: string | null;
  resolution_notes: string | null;
  created_by_user_id: UUID | null;
  reviewed_by_user_id: UUID | null;
  reviewed_at: string | null;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export function listOperatorReviewItems(workspaceId: UUID): Promise<ApiResult<OperatorReviewItem[]>> {
  return apiGet<OperatorReviewItem[]>("/operator-reviews", {
    optional: true,
    query: {
      workspace_id: workspaceId,
      limit: 100,
    },
  });
}
