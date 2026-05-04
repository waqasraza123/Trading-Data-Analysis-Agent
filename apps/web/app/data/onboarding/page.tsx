import { OnboardingWorkflow } from "@/components/data-onboarding/OnboardingWorkflow";
import { AppShell } from "@/components/layout/app-shell";
import { getPublicEnv } from "@/config/env";
import { listDataSources } from "@/lib/api/dataSources";
import { listMarketMemorySnapshots, listSymbols, listWorkspaces } from "@/lib/api/market";
import {
  getProviderHealthSummary,
  listProviderHealthSnapshots,
} from "@/lib/api/providerHealth";
import type { ApiFailure, ApiResult } from "@/lib/api/types";
import type { OnboardingFailure, OnboardingInitialData } from "@/lib/data-onboarding/types";

type DataOnboardingPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
  }>;
};

export default async function DataOnboardingPage({ searchParams }: DataOnboardingPageProps) {
  const params = await searchParams;
  const data = await getOnboardingData(params.workspaceId);

  return (
    <AppShell appName={data.appName}>
      <OnboardingWorkflow initialData={data} />
    </AppShell>
  );
}

async function getOnboardingData(workspaceId?: string): Promise<OnboardingInitialData> {
  const env = getPublicEnv();
  const failures: OnboardingFailure[] = [];
  const [workspacesResult, symbolsResult] = await Promise.all([listWorkspaces(), listSymbols()]);
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const symbols = readResult("Symbols", symbolsResult, [], failures);
  const workspace =
    workspaces.find((candidate) => candidate.id === workspaceId) || workspaces[0] || null;

  if (!workspace) {
    return {
      appName: env.appName,
      apiBaseUrl: env.apiBaseUrl,
      workspace,
      workspaces,
      symbols,
      dataSources: [],
      memorySnapshots: [],
      providerHealthSnapshots: [],
      providerHealthSummary: null,
      failures,
      lastUpdatedAt: new Date().toISOString(),
    };
  }

  const [dataSourcesResult, memoryResult, providerHealthResult, providerHealthSummaryResult] =
    await Promise.all([
    listDataSources(workspace.id),
    listMarketMemorySnapshots(workspace.id),
    listProviderHealthSnapshots({ workspaceId: workspace.id }),
    getProviderHealthSummary(workspace.id),
  ]);

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    workspace,
    workspaces,
    symbols,
    dataSources: readResult("Data sources", dataSourcesResult, [], failures),
    memorySnapshots: readResult("Market memory", memoryResult, [], failures),
    providerHealthSnapshots: readResult(
      "Provider health",
      providerHealthResult,
      [],
      failures,
    ),
    providerHealthSummary: readResult(
      "Provider health summary",
      providerHealthSummaryResult,
      null,
      failures,
    ),
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: OnboardingFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function toFailure(label: string, result: ApiFailure): OnboardingFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
