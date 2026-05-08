import { AppShell } from "@/components/layout/AppShell";
import { SymbolDetailView } from "@/components/market/symbol-detail-view";
import { getPublicEnv } from "@/config/env";
import { AnimatedSection } from "@/lib/ui/motion";
import { listAnalysisRuns, listMarketMemorySnapshots, listWorkspaces, getSymbol } from "@/lib/api/market";
import { listSignalOutcomes } from "@/lib/api/outcomes";
import { listDashboardSymbolReadModels } from "@/lib/api/readModels";
import { getAnalysisRunSignal } from "@/lib/api/signals";
import type { DashboardSymbolReadModel, MarketMemorySnapshot } from "@/lib/api/types";
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
  const symbolReadModelsResult = workspace
    ? await listDashboardSymbolReadModels({ workspaceId: workspace.id, symbolId, limit: 100 })
    : null;

  const analysisRuns = runsResult?.ok ? runsResult.data : [];
  const signalResults = await Promise.all(analysisRuns.slice(0, 8).map((run) => getAnalysisRunSignal(run.id)));
  const signals = signalResults.flatMap((result) => (result.ok ? [result.data] : []));
  const outcomeResults = await Promise.all(signals.slice(0, 3).map((signal) => listSignalOutcomes(signal.signal.id)));
  const outcomes = outcomeResults.flatMap((result) => (result.ok ? result.data : []));
  const scheduledScans = (scansResult?.ok ? scansResult.data : []).filter(
    (scan) => scan.symbol_id === symbolId || scan.watchlist_id !== null,
  );

  return (
    <AppShell appName={env.appName} workspaceId={workspace?.id} workspaceName={workspace?.name}>
      <AnimatedSection as="section">
        <SymbolDetailView
        symbol={symbolResult.ok ? symbolResult.data : null}
        workspace={workspace}
        memorySnapshots={
          symbolReadModelsResult?.ok && symbolReadModelsResult.data.length > 0
            ? symbolReadModelsResult.data.map(memoryFromSymbolReadModel)
            : memoryResult?.ok
            ? memoryResult.data
            : []
        }
        analysisRuns={analysisRuns}
        signals={signals}
        outcomes={outcomes}
        scheduledScans={scheduledScans}
        />
      </AnimatedSection>
    </AppShell>
  );
}

function memoryFromSymbolReadModel(model: DashboardSymbolReadModel): MarketMemorySnapshot {
  return {
    id: model.id,
    workspace_id: model.workspace_id,
    symbol_id: model.symbol_id,
    source_id: model.source_id,
    timeframe: model.timeframe,
    state_version: model.read_model_version,
    latest_final_candle_time: model.latest_final_candle_time,
    latest_analysis_run_id: null,
    latest_signal_id: model.latest_signal_id,
    latest_outcome_id: null,
    data_quality_label: model.data_quality_label || "unknown",
    freshness_label: model.freshness_label || "unknown",
    trend_state: null,
    volatility_state: null,
    range_state: null,
    market_regime_label: model.market_regime_label,
    market_session_label: model.market_session_label,
    multi_timeframe_label: null,
    cross_asset_label: null,
    latest_signal_bias: model.latest_bias,
    latest_signal_pattern_type: model.latest_pattern_type,
    latest_signal_confidence_label: model.latest_confidence_label,
    context_json: model.summary_json,
    warnings_json: readJsonArray(model.summary_json.warnings),
    created_at: model.created_at,
    updated_at: model.updated_at,
  };
}

function readJsonArray(value: unknown): Array<Record<string, string | number | boolean | null>> {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, string | number | boolean | null> =>
        Boolean(item) && typeof item === "object" && !Array.isArray(item),
      )
    : [];
}
