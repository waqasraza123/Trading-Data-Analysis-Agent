import { EmptyState } from "@/components/empty-states/empty-state";
import { AppShell } from "@/components/layout/AppShell";
import { Panel } from "@/components/layout/panel";
import { ReadinessBlockers } from "@/components/readiness/ReadinessBlockers";
import { ReadinessChecklist } from "@/components/readiness/ReadinessChecklist";
import { ReadinessEmptyState } from "@/components/readiness/ReadinessEmptyState";
import { ReadinessHeader } from "@/components/readiness/ReadinessHeader";
import { ReadinessRemediationPanel } from "@/components/readiness/ReadinessRemediationPanel";
import { ReadinessRunButton } from "@/components/readiness/ReadinessRunButton";
import { ReadinessScoreCard } from "@/components/readiness/ReadinessScoreCard";
import { getPublicEnv } from "@/config/env";
import {
  getLatestProductReadiness,
  getProductReadinessRun,
  listProductReadinessRuns,
} from "@/lib/api/productReadiness";
import { listWorkspaces } from "@/lib/api/market";
import { AnimatedSection } from "@/components/ui/motion";
import type { ApiFailure, ApiResult } from "@/lib/api/types";
import type { ProductReadinessPageData, ProductReadinessRun, ReadinessFailure } from "@/lib/readiness/types";

type ReadinessPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    runId?: string;
  }>;
};

export default async function ReadinessPage({ searchParams }: ReadinessPageProps) {
  const params = await searchParams;
  const data = await getReadinessPageData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <ReadinessHeader data={data} />
        {!data.workspace && (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before workspace-scoped readiness can validate daily-use setup."
          />
        )}
        <ReadinessFailures failures={data.failures} />
        <Panel
          title="Run checklist"
          eyebrow="Explicit validation"
          action={<ReadinessRunButton workspaceId={data.workspace?.id || null} />}
        >
          <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">
            The checklist reads current product state and saves an auditable readiness run. It does not seed data, run daily workflows, start workers, send notifications, fetch providers, execute broker actions, auto-trade, or produce financial advice.
          </p>
        </Panel>
        {data.selectedRun ? (
          <>
            <ReadinessScoreCard run={data.selectedRun} />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
              <ReadinessChecklist run={data.selectedRun} workspaceId={data.workspace?.id} />
              <div className="space-y-6">
                <ReadinessBlockers
                  blockers={data.selectedRun.blockers_json}
                  warnings={data.selectedRun.warnings_json}
                  workspaceId={data.workspace?.id}
                />
                <ReadinessRemediationPanel run={data.selectedRun} workspaceId={data.workspace?.id} />
              </div>
            </div>
          </>
        ) : (
          <ReadinessEmptyState workspaceId={data.workspace?.id} />
        )}
      </AnimatedSection>
    </AppShell>
  );
}

async function getReadinessPageData(params: {
  workspaceId?: string;
  runId?: string;
}): Promise<ProductReadinessPageData> {
  const env = getPublicEnv();
  const failures: ReadinessFailure[] = [];
  const workspacesResult = await listWorkspaces();
  const workspaces = readResult("Workspaces", workspacesResult, [], failures);
  const workspace =
    workspaces.find((candidate) => candidate.id === params.workspaceId) || workspaces[0] || null;
  const [latestResult, runsResult, selectedResult] = await Promise.all([
    getLatestProductReadiness(workspace?.id || null),
    listProductReadinessRuns(workspace?.id || null),
    params.runId ? getProductReadinessRun(params.runId) : Promise.resolve(null),
  ]);
  const latestRun = readOptionalRun("Latest readiness", latestResult, failures);
  const recentRuns = readOptionalRunList("Readiness runs", runsResult, failures);
  const selectedRun = selectedResult
    ? readOptionalRun("Selected readiness", selectedResult, failures)
    : latestRun;

  return {
    appName: env.appName,
    apiBaseUrl: env.apiBaseUrl,
    workspace,
    workspaces,
    selectedRun,
    latestRun,
    recentRuns,
    failures,
    lastUpdatedAt: new Date().toISOString(),
  };
}

function ReadinessFailures({ failures }: { failures: ReadinessFailure[] }) {
  const visibleFailures = failures.filter((failure) => !failure.missing);
  if (visibleFailures.length === 0) {
    return null;
  }
  return (
    <Panel title="Backend state" eyebrow={`${visibleFailures.length} issue(s)`}>
      <div className="grid gap-3">
        {visibleFailures.map((failure) => (
          <div key={`${failure.label}-${failure.status}`} className="muted-surface rounded-lg p-4">
            <p className="font-semibold text-[var(--strong)]">{failure.label}</p>
            <p className="mt-1 text-sm text-slate-500">{failure.message}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function readResult<T>(
  label: string,
  result: ApiResult<T>,
  fallback: T,
  failures: ReadinessFailure[],
): T {
  if (result.ok) {
    return result.data;
  }
  failures.push(toFailure(label, result));
  return fallback;
}

function readOptionalRun(
  label: string,
  result: ApiResult<ProductReadinessRun>,
  failures: ReadinessFailure[],
): ProductReadinessRun | null {
  if (result.ok) {
    return result.data;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return null;
}

function readOptionalRunList(
  label: string,
  result: Awaited<ReturnType<typeof listProductReadinessRuns>>,
  failures: ReadinessFailure[],
): ProductReadinessRun[] {
  if (result.ok) {
    return result.data.runs;
  }
  if (!result.error.missing) {
    failures.push(toFailure(label, result));
  }
  return [];
}

function toFailure(label: string, result: ApiFailure): ReadinessFailure {
  return {
    label,
    status: result.error.status,
    message: result.error.message,
    missing: result.error.missing,
  };
}
