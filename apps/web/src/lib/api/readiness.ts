import { apiGet } from "./client";
import type {
  ApiResult,
  DecisionReadinessAssessmentResponse,
  JsonRecord,
  UUID,
} from "./types";

export type DecisionReadinessAssessmentRead = {
  id: UUID;
  workspace_id: UUID;
  source_type: string;
  source_id: UUID;
  analysis_run_id: UUID | null;
  signal_id: UUID | null;
  assessment_version: string;
  readiness_score: number;
  readiness_label: string;
  status: string;
  required_checks_json: JsonRecord[];
  optional_checks_json: JsonRecord[];
  blockers_json: JsonRecord[];
  warnings_json: JsonRecord[];
  next_steps_json: string[];
  summary: string;
  metadata_json: JsonRecord;
  created_at: string;
  updated_at: string;
};

export type DecisionReadinessAssessmentListResponse = {
  assessments: DecisionReadinessAssessmentRead[];
};

export function getLatestSignalReadiness(
  signalId: UUID,
): Promise<ApiResult<DecisionReadinessAssessmentResponse>> {
  return apiGet<DecisionReadinessAssessmentResponse>(
    `/decision-readiness/signals/${signalId}/latest`,
    { optional: true },
  );
}

export function listDecisionReadinessAssessments(
  workspaceId: UUID,
): Promise<ApiResult<DecisionReadinessAssessmentListResponse>> {
  return apiGet<DecisionReadinessAssessmentListResponse>("/decision-readiness", {
    optional: true,
    query: {
      workspaceId,
      limit: 100,
    },
  });
}
