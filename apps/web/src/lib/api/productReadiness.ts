import { apiGet, apiPost } from "./client";
import type { ApiResult, UUID } from "./types";
import type { ProductReadinessRun, ProductReadinessRunListResponse } from "@/lib/readiness/types";

export function runProductReadiness(
  workspaceId?: UUID | null,
): Promise<ApiResult<ProductReadinessRun>> {
  return apiPost<ProductReadinessRun>(
    "/product-readiness/run",
    workspaceId ? { workspace_id: workspaceId } : {},
    {
      query: {
        workspaceId: workspaceId || undefined,
      },
      optional: true,
      timeoutMs: 10000,
    },
  );
}

export function getLatestProductReadiness(
  workspaceId?: UUID | null,
): Promise<ApiResult<ProductReadinessRun>> {
  return apiGet<ProductReadinessRun>("/product-readiness/latest", {
    query: {
      workspaceId: workspaceId || undefined,
    },
    optional: true,
  });
}

export function getProductReadinessRun(runId: UUID): Promise<ApiResult<ProductReadinessRun>> {
  return apiGet<ProductReadinessRun>(`/product-readiness/runs/${runId}`, { optional: true });
}

export function listProductReadinessRuns(
  workspaceId?: UUID | null,
): Promise<ApiResult<ProductReadinessRunListResponse>> {
  return apiGet<ProductReadinessRunListResponse>("/product-readiness/runs", {
    query: {
      workspaceId: workspaceId || undefined,
      limit: 25,
    },
    optional: true,
  });
}
