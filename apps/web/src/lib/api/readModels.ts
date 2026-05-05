import { apiGet } from "./client";
import type {
  ApiResult,
  CommandCenterReadModel,
  DashboardSymbolReadModel,
  SignalCardReadModel,
  UUID,
} from "./types";

export function listDashboardSymbolReadModels(params: {
  workspaceId: UUID;
  symbolId?: UUID;
  sourceId?: UUID;
  timeframe?: string;
  freshnessLabel?: string;
  dataQualityLabel?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResult<DashboardSymbolReadModel[]>> {
  return apiGet<DashboardSymbolReadModel[]>("/read-models/symbols", {
    optional: true,
    query: params,
  });
}

export function listSignalCardReadModels(params: {
  workspaceId: UUID;
  symbolId?: UUID;
  timeframe?: string;
  classificationStatus?: string;
  bias?: string;
  reviewBucket?: string;
  priorityLabel?: string;
  freshnessLabel?: string;
  dataQualityLabel?: string;
  readinessLabel?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<ApiResult<SignalCardReadModel[]>> {
  return apiGet<SignalCardReadModel[]>("/read-models/signals", {
    optional: true,
    query: params,
  });
}

export function getCommandCenterReadModel(
  workspaceId: UUID,
): Promise<ApiResult<CommandCenterReadModel>> {
  return apiGet<CommandCenterReadModel>("/read-models/command-center", {
    optional: true,
    query: { workspaceId },
  });
}
