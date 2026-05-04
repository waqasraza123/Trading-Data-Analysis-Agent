import Link from "next/link";
import { EmptyState } from "@/components/empty-states/empty-state";
import { Panel } from "@/components/layout/panel";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { OutcomeList } from "@/components/outcomes/outcome-list";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type {
  AnalysisRun,
  MarketMemorySnapshot,
  ScheduledScanConfig,
  SignalClassification,
  SignalOutcome,
  SymbolRead,
  Workspace,
} from "@/lib/api/types";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";

type SymbolDetailViewProps = {
  symbol: SymbolRead | null;
  workspace: Workspace | null;
  memorySnapshots: MarketMemorySnapshot[];
  analysisRuns: AnalysisRun[];
  signals: SignalClassification[];
  outcomes: SignalOutcome[];
  scheduledScans: ScheduledScanConfig[];
};

export function SymbolDetailView({
  symbol,
  workspace,
  memorySnapshots,
  analysisRuns,
  signals,
  outcomes,
  scheduledScans,
}: SymbolDetailViewProps) {
  if (!symbol) {
    return <EmptyState title="Symbol not available" message="The API did not return metadata for this symbol." />;
  }

  return (
    <div className="space-y-6">
      <Panel title={symbol.symbol} eyebrow="Symbol state">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-lg font-semibold text-[var(--strong)]">{symbol.display_name}</p>
            <p className="mt-2 text-sm text-slate-500">
              {humanizeLabel(symbol.market_type)} {symbol.base_asset && symbol.quote_asset ? `${symbol.base_asset}/${symbol.quote_asset}` : ""}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge value={symbol.is_active ? "Active" : "Inactive"} tone={symbol.is_active ? "good" : "warning"} />
            <Badge value={workspace?.name || "No workspace"} tone="info" />
          </div>
        </div>
        <WorkflowLinks workspaceId={workspace?.id} targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review"]} className="mt-5" />
      </Panel>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <Panel title="Timeframe States" eyebrow="Market memory">
            {memorySnapshots.length === 0 ? (
              <EmptyState title="No market memory" message="No rolling state snapshots were returned for this symbol." />
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {memorySnapshots.map((snapshot) => (
                  <div key={snapshot.id} className="muted-surface rounded-lg p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <Badge value={snapshot.timeframe} tone="info" />
                      <span className="text-sm text-slate-500">{formatRelativeTime(snapshot.latest_final_candle_time)}</span>
                    </div>
                    <div className="mt-4 flex flex-wrap gap-2">
                      <Badge value={snapshot.freshness_label} tone={toneForQuality(snapshot.freshness_label)} />
                      <Badge value={snapshot.data_quality_label} tone={toneForQuality(snapshot.data_quality_label)} />
                      <Badge value={snapshot.latest_signal_bias || "No directional signal"} tone={toneForBias(snapshot.latest_signal_bias)} />
                    </div>
                    <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                      <Detail label="Pattern" value={humanizeLabel(snapshot.latest_signal_pattern_type)} />
                      <Detail label="Regime" value={humanizeLabel(snapshot.market_regime_label)} />
                      <Detail label="Session" value={humanizeLabel(snapshot.market_session_label)} />
                      <Detail label="Updated" value={formatDateTime(snapshot.updated_at)} />
                    </dl>
                  </div>
                ))}
              </div>
            )}
          </Panel>
          <Panel title="Latest Signals" eyebrow="Analysis outputs">
            {signals.length === 0 ? (
              <EmptyState title="No latest signals" message="Recent analysis runs did not return signal classifications." />
            ) : (
              <div className="space-y-3">
                {signals.map((classification) => (
                  <Link
                    key={classification.signal.id}
                    href={`/signals/${classification.signal.id}`}
                    className="block rounded-lg border border-[var(--line)] p-4 hover:bg-[var(--panel-muted)]"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="font-semibold text-[var(--strong)]">{humanizeLabel(classification.signal.bias)}</p>
                        <p className="mt-1 text-sm text-slate-500">{classification.signal.summary}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <Badge value={classification.signal.timeframe} tone="info" />
                        <Badge value={classification.signal.confidence_label} tone={toneForQuality(classification.signal.confidence_label)} />
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Panel>
          <Panel title="Recent Outcomes" eyebrow="Observed horizons">
            <OutcomeList outcomes={outcomes} />
          </Panel>
        </div>
        <aside className="space-y-6">
          <Panel title="Scheduled Scans" eyebrow="Backend scan configs">
            {scheduledScans.length === 0 ? (
              <EmptyState title="No scan configs" message="No scheduled scans were returned for this symbol." />
            ) : (
              <div className="space-y-3">
                {scheduledScans.map((scan) => (
                  <div key={scan.id} className="muted-surface rounded-lg p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h3 className="font-semibold text-[var(--strong)]">{scan.name}</h3>
                      <Badge value={scan.status} tone={toneForQuality(scan.status)} />
                    </div>
                    <p className="mt-2 text-sm text-slate-500">Next run {formatDateTime(scan.next_run_at)}</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>
          <Panel title="Analysis Runs" eyebrow="Recent backend runs">
            {analysisRuns.length === 0 ? (
              <EmptyState title="No analysis runs" message="The API did not return recent runs for this symbol." />
            ) : (
              <div className="space-y-3">
                {analysisRuns.map((run) => (
                  <div key={run.id} className="muted-surface rounded-lg p-4">
                    <div className="flex flex-wrap gap-2">
                      <Badge value={run.status} tone={toneForQuality(run.status)} />
                      <Badge value={run.timeframe} tone="info" />
                    </div>
                    <p className="mt-3 text-sm text-slate-500">{shortIdentifier(run.id)}</p>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </aside>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}
