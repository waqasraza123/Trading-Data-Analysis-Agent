import type { JsonRecord, UUID, Workspace } from "@/lib/api/types";

export type ProductReadinessRunStatus = "completed" | "completed_with_warnings" | "failed";
export type ProductReadinessLabel = "ready" | "needs_setup" | "degraded" | "blocked" | "unknown";
export type ProductReadinessCheckStatus = "passed" | "warning" | "failed" | "skipped";

export type ProductReadinessCheck = {
  key: string;
  status: ProductReadinessCheckStatus;
  title: string;
  summary: string;
  remediation: string;
  related_route: string | null;
  metadata: JsonRecord;
};

export type ProductReadinessRun = {
  id: UUID;
  workspace_id: UUID | null;
  status: ProductReadinessRunStatus;
  readiness_version: string;
  readiness_score: number;
  readiness_label: ProductReadinessLabel;
  summary: string;
  checks_json: ProductReadinessCheck[];
  blockers_json: ProductReadinessCheck[];
  warnings_json: ProductReadinessCheck[];
  created_at: string;
  updated_at: string;
};

export type ProductReadinessRunListResponse = {
  runs: ProductReadinessRun[];
};

export type ReadinessFailure = {
  label: string;
  status: number;
  message: string;
  missing: boolean;
};

export type ProductReadinessPageData = {
  appName: string;
  apiBaseUrl: string;
  workspace: Workspace | null;
  workspaces: Workspace[];
  selectedRun: ProductReadinessRun | null;
  latestRun: ProductReadinessRun | null;
  recentRuns: ProductReadinessRun[];
  failures: ReadinessFailure[];
  lastUpdatedAt: string;
};
