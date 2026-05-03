import { AppShell } from "@/components/layout/app-shell";
import { SymbolDetailView } from "@/components/market/symbol-detail-view";
import { getPublicEnv } from "@/config/env";
import { listAnalysisRuns, listMarketMemorySnapshots, listWorkspaces, getSymbol } from "@/lib/api/market";
import { listSignalOutcomes } from "@/lib/api/outcomes";
import { getAnalysisRunSignal } from "@/lib/api/signals";
import { listScheduledScanConfigs } from "@/lib/api/watchlists";

type SymbolPageProps = {
  params: Promise<{
    symbolId: string;
  }>;
  searchParams: Promise<{
    workspaceId?: string;
  }>;
};

export default async function SymbolPage({ params, searchParams }: SymbolPageProps) {
  const [{ symbolId }, query] = await Promise.all([params, searchParams]);
  const env = getPublicEnv();
  const [symbolResult, workspacesResult] = await Promise.all([getSymbol(symbolId), listWorkspaces()]);
  const workspaces = workspacesResult.ok ? workspacesResult.data : [];
  const workspace = workspaces.find((candidate) => candidate.id === query.workspaceId) || workspaces[0] || null;

  const [memoryResult, runsResult, scansResult] = workspace
    ? await Promise.all([
        listMarketMemorySnapshots(workspace.id, symbolId),
        listAnalysisRuns(workspace.id, symbolId),
        listScheduledScanConfigs(workspace.id),
      ])
    : [null, null, null];

  const analysisRuns = runsResult?.ok ? runsResult.data : [];
  const signalResults = await Promise.all(analysisRuns.slice(0, 8).map((run) => getAnalysisRunSignal(run.id)));
  const signals = signalResults.flatMap((result) => (result.ok ? [result.data] : []));
  const outcomeResults = await Promise.all(signals.slice(0, 3).map((signal) => listSignalOutcomes(signal.signal.id)));
  const outcomes = outcomeResults.flatMap((result) => (result.ok ? result.data : []));
  const scheduledScans = (scansResult?.ok ? scansResult.data : []).filter(
    (scan) => scan.symbol_id === symbolId || scan.watchlist_id !== null,
  );

  return (
    <AppShell appName={env.appName}>
      <SymbolDetailView
        symbol={symbolResult.ok ? symbolResult.data : null}
        workspace={workspace}
        memorySnapshots={memoryResult?.ok ? memoryResult.data : []}
        analysisRuns={analysisRuns}
        signals={signals}
        outcomes={outcomes}
        scheduledScans={scheduledScans}
      />
    </AppShell>
  );
}
