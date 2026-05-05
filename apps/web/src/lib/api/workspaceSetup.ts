import { getPublicEnv } from "@/config/env";
import { getLatestProductReadiness } from "./productReadiness";
import { listDataSources } from "./dataSources";
import { listWorkspaces, listSymbols } from "./market";
import { listProviderCredentialRefs } from "./providerCredentials";
import { listScannerPresets, listScannerScanConfigs } from "./scanner";
import { apiGet, apiPost } from "./client";
import type { ApiFailure, ApiResult, JsonRecord, UUID } from "./types";
import type {
  SetupDemoWorkspaceResponse,
  SetupWizardFailure,
  SetupWizardInitialData,
  WorkspaceSetupRun,
  WorkspaceSetupStepKey,
} from "@/lib/setup-wizard/types";

export function startWorkspaceSetup(input: {
  workspace_id?: UUID;
  user_id?: UUID;
  initial_context_json?: JsonRecord;
}): Promise<ApiResult<WorkspaceSetupRun>> {
  return apiPost<WorkspaceSetupRun>("/workspace-setup/start", input, {
    optional: true,
    timeoutMs: 12000,
  });
}

export function getWorkspaceSetupRun(setupRunId: UUID): Promise<ApiResult<WorkspaceSetupRun>> {
  return apiGet<WorkspaceSetupRun>(`/workspace-setup/runs/${setupRunId}`, { optional: true });
}

export function completeWorkspaceSetupStep(
  setupRunId: UUID,
  stepKey: WorkspaceSetupStepKey,
  input: Record<string, unknown>,
): Promise<ApiResult<WorkspaceSetupRun>> {
  return apiPost<WorkspaceSetupRun>(
    `/workspace-setup/runs/${setupRunId}/steps/${stepKey}`,
    { input },
    { optional: true, timeoutMs: stepKey === "first_scan" ? 60000 : 30000 },
  );
}

export function skipWorkspaceSetupStep(
  setupRunId: UUID,
  stepKey: WorkspaceSetupStepKey,
): Promise<ApiResult<WorkspaceSetupRun>> {
  return apiPost<WorkspaceSetupRun>(
    `/workspace-setup/runs/${setupRunId}/steps/${stepKey}/skip`,
    {},
    { optional: true },
  );
}

export function finishWorkspaceSetup(setupRunId: UUID): Promise<ApiResult<WorkspaceSetupRun>> {
  return apiPost<WorkspaceSetupRun>(`/workspace-setup/runs/${setupRunId}/finish`, {}, {
    optional: true,
    timeoutMs: 20000,
  });
}

export function createSetupDemoWorkspace(input: {
  workspace_name: string;
  operator_email: string;
  operator_name: string;
  market_type: string;
  symbol_codes: string[];
  timeframes: string[];
  seed_demo_data: boolean;
}): Promise<ApiResult<SetupDemoWorkspaceResponse>> {
  return apiPost<SetupDemoWorkspaceResponse>("/workspace-setup/demo-workspace", input, {
    optional: true,
    timeoutMs: 60000,
  });
}

export async function getSetupWizardInitialData(params: {
  workspaceId?: string;
}): Promise<SetupWizardInitialData> {
  const env = getPublicEnv();
  const failures: SetupWizardFailure[] = [];
  const [workspacesResult, symbolsResult] = await Promise.all([listWorkspaces(), listSymbols()]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const selectedWorkspace =
    workspaces.find((workspace) => workspace.id === params.workspaceId) || workspaces[0] || null;
  if (!selectedWorkspace) {
    return {
      appName: env.appName,
      workspaces,
      symbols,
      dataSources: [],
      providerCredentialRefs: [],
      scannerPresets: [],
      scanConfigs: [],
      readinessRun: null,
      failures,
      selectedWorkspaceId: null,
    };
  }
  const [
    dataSourcesResult,
    credentialRefsResult,
    presetsResult,
    readinessResult,
    scanConfigsResult,
  ] = await Promise.all([
    listDataSources(selectedWorkspace.id),
    listProviderCredentialRefs(selectedWorkspace.id),
    listScannerPresets(selectedWorkspace.id),
    getLatestProductReadiness(selectedWorkspace.id),
    listScannerScanConfigs(selectedWorkspace.id),
  ]);
  const dataSources = readResult("Data sources", dataSourcesResult, [], failures);
  const scanConfigs = readResult("Scan configs", scanConfigsResult, [], failures);
  return {
    appName: env.appName,
    workspaces,
    symbols,
    dataSources,
    providerCredentialRefs: readResult("Provider credentials", credentialRefsResult, [], failures),
    scannerPresets: readResult("Scanner presets", presetsResult, [], failures),
    scanConfigs,
    readinessRun: readNullable("Readiness", readinessResult, failures),
    failures,
    selectedWorkspaceId: selectedWorkspace.id,
  };
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: SetupWizardFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readNullable<T>(
  label: string,
  result: ApiResult<T>,
  failures: SetupWizardFailure[],
): T | null {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function toFailure(label: string, result: ApiFailure): SetupWizardFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
