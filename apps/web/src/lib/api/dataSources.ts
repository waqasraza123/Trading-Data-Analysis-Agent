import { apiGet } from "./client";
import { apiPostJson } from "./postClient";
import type { ApiResult, UUID } from "./types";
import type { DataSource, DataSourceCreate } from "@/lib/data-onboarding/types";

export function listDataSources(workspaceId: UUID): Promise<ApiResult<DataSource[]>> {
  return apiGet<DataSource[]>("/data-sources", {
    query: {
      workspace_id: workspaceId,
      limit: 500,
    },
    optional: true,
  });
}

export function createDataSource(payload: DataSourceCreate): Promise<ApiResult<DataSource>> {
  return apiPostJson<DataSource>("/data-sources", payload, { optional: true });
}
