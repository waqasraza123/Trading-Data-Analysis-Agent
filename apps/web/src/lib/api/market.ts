import { apiGet } from "./client";
import type {
  AnalysisRun,
  ApiResult,
  MarketMemorySnapshot,
  SymbolRead,
  UUID,
  Workspace,
} from "./types";
import type { WorkspaceDefaultContext } from "@/lib/workspace/types";

export function listWorkspaces(): Promise<ApiResult<Workspace[]>> {
  return apiGet<Workspace[]>("/workspaces", {
    query: {
      limit: 100,
    },
    optional: true,
  });
}

export function getWorkspaceDefaultContext(): Promise<ApiResult<WorkspaceDefaultContext>> {
  return apiGet<WorkspaceDefaultContext>("/workspaces/default-context", {
    optional: true,
  });
}

export function listSymbols(): Promise<ApiResult<SymbolRead[]>> {
  return apiGet<SymbolRead[]>("/symbols", {
    query: {
      is_active: true,
      limit: 500,
    },
    optional: true,
  });
}

export function getSymbol(symbolId: UUID): Promise<ApiResult<SymbolRead>> {
  return apiGet<SymbolRead>(`/symbols/${symbolId}`, { optional: true });
}

export function listMarketMemorySnapshots(
  workspaceId: UUID,
  symbolId?: UUID,
): Promise<ApiResult<MarketMemorySnapshot[]>> {
  return apiGet<MarketMemorySnapshot[]>("/market-memory/snapshots", {
    query: {
      workspaceId,
      symbolId,
      limit: 500,
    },
    optional: true,
  });
}

export function listAnalysisRuns(
  workspaceId: UUID,
  symbolId?: UUID,
): Promise<ApiResult<AnalysisRun[]>> {
  return apiGet<AnalysisRun[]>("/analysis-runs", {
    query: {
      workspace_id: workspaceId,
      symbol_id: symbolId,
      limit: 25,
    },
    optional: true,
  });
}
