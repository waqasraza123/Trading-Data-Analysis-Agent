import Link from "next/link";
import { EmptyState } from "@/components/empty-states/empty-state";
import { Panel } from "@/components/layout/panel";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { OutcomeList } from "@/components/outcomes/outcome-list";
import { Badge, toneForQuality } from "@/components/status/badge";
import { BiasBadge } from "@/components/status/BiasBadge";
import { ConfidenceBadge } from "@/components/status/ConfidenceBadge";
import { DataQualityBadge } from "@/components/status/DataQualityBadge";
import { FreshnessBadge } from "@/components/status/FreshnessBadge";
import { PageHeader } from "@/components/ui/PageHeader";
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
import {
  AnimatedListItem,
  AnimatedSection,
  motionRevealDensityStyle,
} from "@/lib/ui/motion";

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
    <AnimatedSection as="section" className="space-y-6">
      <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")} preset="fade-up">
        <PageHeader
          eyebrow="Symbol state"
          title={symbol.symbol}
          description={`${symbol.display_name} · ${humanizeLabel(symbol.market_type)} ${symbol.base_asset && symbol.quote_asset ? `${symbol.base_asset}/${symbol.quote_asset}` : ""}`.trim()}
          meta={
            <>
              <Badge value={symbol.is_active ? "Active" : "Inactive"} tone={symbol.is_active ? "good" : "warning"} />
              <Badge value={workspace?.name || "No workspace"} tone="info" />
            </>
          }
          actions={
            <WorkflowLinks
              workspaceId={workspace?.id}
              targets={["commandCenter", "brief", "triage", "scanner", "dataOnboarding", "review"]}
            />
          }
        />
      </AnimatedListItem>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "regular")} preset="scale-subtle">
            <Panel title="Timeframe States" eyebrow="Market memory">
              {memorySnapshots.length === 0 ? (
                <EmptyState
                  title="No market memory"
                  message="No rolling state snapshots were returned for this symbol."
                />
              ) : (
                <div className="grid gap-4 lg:grid-cols-2">
                  {memorySnapshots.map((snapshot, index) => (
                    <AnimatedListItem
                      as="section"
                      key={snapshot.id}
                      className="muted-surface rounded-lg p-4"
                      preset="scale-subtle"
                      style={motionRevealDensityStyle(index, "compact")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <Badge value={snapshot.timeframe} tone="info" />
                        <span className="text-sm text-slate-500">
                          {formatRelativeTime(snapshot.latest_final_candle_time)}
                        </span>
                      </div>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <FreshnessBadge value={snapshot.freshness_label} />
                        <DataQualityBadge value={snapshot.data_quality_label} />
                        <BiasBadge value={snapshot.latest_signal_bias || "No directional signal"} />
                      </div>
                      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
                        <Detail label="Pattern" value={humanizeLabel(snapshot.latest_signal_pattern_type)} />
                        <Detail label="Regime" value={humanizeLabel(snapshot.market_regime_label)} />
                        <Detail label="Session" value={humanizeLabel(snapshot.market_session_label)} />
                        <Detail label="Updated" value={formatDateTime(snapshot.updated_at)} />
                      </dl>
                    </AnimatedListItem>
                  ))}
                </div>
              )}
            </Panel>
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "regular")} preset="scale-subtle">
            <Panel title="Latest Signals" eyebrow="Analysis outputs">
              {signals.length === 0 ? (
                <EmptyState title="No latest signals" message="Recent analysis runs did not return signal classifications." />
              ) : (
                <div className="space-y-3">
                  {signals.map((classification, index) => (
                    <AnimatedListItem
                      as="section"
                      key={classification.signal.id}
                      preset="scale-subtle"
                      style={motionRevealDensityStyle(index, "compact")}
                    >
                      <Link
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
                            <ConfidenceBadge value={classification.signal.confidence_label} />
                          </div>
                        </div>
                      </Link>
                    </AnimatedListItem>
                  ))}
                </div>
              )}
            </Panel>
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "regular")} preset="fade-up">
            <Panel title="Recent Outcomes" eyebrow="Observed horizons">
              <OutcomeList outcomes={outcomes} />
            </Panel>
          </AnimatedListItem>
        </div>
        <aside className="space-y-6">
          <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "regular")} preset="scale-subtle">
            <Panel title="Scheduled Scans" eyebrow="Backend scan configs">
              {scheduledScans.length === 0 ? (
                <EmptyState title="No scan configs" message="No scheduled scans were returned for this symbol." />
              ) : (
                <div className="space-y-3">
                  {scheduledScans.map((scan, index) => (
                    <AnimatedListItem
                      as="section"
                      key={scan.id}
                      className="muted-surface rounded-lg p-4"
                      preset="scale-subtle"
                      style={motionRevealDensityStyle(index, "compact")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <h3 className="font-semibold text-[var(--strong)]">{scan.name}</h3>
                        <Badge value={scan.status} tone={toneForQuality(scan.status)} />
                      </div>
                      <p className="mt-2 text-sm text-slate-500">Next run {formatDateTime(scan.next_run_at)}</p>
                    </AnimatedListItem>
                  ))}
                </div>
              )}
            </Panel>
          </AnimatedListItem>
          <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "regular")} preset="scale-subtle">
            <Panel title="Analysis Runs" eyebrow="Recent backend runs">
              {analysisRuns.length === 0 ? (
                <EmptyState title="No analysis runs" message="The API did not return recent runs for this symbol." />
              ) : (
                <div className="space-y-3">
                  {analysisRuns.map((run, index) => (
                    <AnimatedListItem
                      as="section"
                      key={run.id}
                      className="muted-surface rounded-lg p-4"
                      preset="scale-subtle"
                      style={motionRevealDensityStyle(index, "compact")}
                    >
                      <div className="flex flex-wrap gap-2">
                        <Badge value={run.status} tone={toneForQuality(run.status)} />
                        <Badge value={run.timeframe} tone="info" />
                      </div>
                      <p className="mt-3 text-sm text-slate-500">{shortIdentifier(run.id)}</p>
                    </AnimatedListItem>
                  ))}
                </div>
              )}
            </Panel>
          </AnimatedListItem>
        </aside>
      </div>
    </AnimatedSection>
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
