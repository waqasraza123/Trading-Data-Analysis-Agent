import Link from "next/link";
import { EmptyState } from "@/components/empty-states/empty-state";
import { EvidenceList } from "@/components/evidence/evidence-list";
import { Panel } from "@/components/layout/panel";
import { OutcomeList } from "@/components/outcomes/outcome-list";
import { ConfidenceList } from "@/components/signals/confidence-list";
import { RiskNoteList } from "@/components/signals/risk-note-list";
import { SetupContextPanel } from "@/components/signals/setup-context-panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type { DashboardData } from "@/lib/api/dashboard";
import { formatDateTime } from "@/lib/formatting/dates";
import { humanizeLabel } from "@/lib/formatting/labels";
import { formatPercent } from "@/lib/formatting/numbers";
import { AnimatedListItem, motionCardClass, motionRevealDensityStyle } from "@/lib/ui/motion";

export function SignalFocusPanel({ data }: { data: DashboardData }) {
  const selectedSignal = data.selectedSignal;

  return (
    <Panel title="Signal Focus" eyebrow="Selected deterministic signal">
      {!selectedSignal ? (
        <EmptyState
          title="No selected signal"
          message="Select a market-board signal or wait for analysis output to appear."
        />
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
          <div className="space-y-5">
            <AnimatedListItem
              as="section"
              className={`${motionCardClass} muted-surface rounded-lg p-4`}
              preset="scale-subtle"
              style={motionRevealDensityStyle(0, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-xl font-semibold text-[var(--strong)]">{humanizeLabel(selectedSignal.signal.bias)}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                    {selectedSignal.signal.summary || selectedSignal.signal.no_signal_reason || "No summary returned."}
                  </p>
                </div>
                <Link
                  className="rounded-md border border-[var(--line)] px-3 py-2 text-sm font-medium hover:bg-white dark:hover:bg-slate-900"
                  href={`/signals/${selectedSignal.signal.id}`}
                >
                  Open detail
                </Link>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Badge value={selectedSignal.signal.bias} tone={toneForBias(selectedSignal.signal.bias)} />
                <Badge value={selectedSignal.signal.pattern_type || "No pattern"} tone="info" />
                <Badge value={selectedSignal.signal.confidence_label} tone={toneForQuality(selectedSignal.signal.confidence_label)} />
                <Badge value={selectedSignal.signal.classification_status} tone={toneForQuality(selectedSignal.signal.classification_status)} />
              </div>
              <dl className="mt-5 grid gap-4 text-sm md:grid-cols-3">
                <Detail label="Confidence" value={formatPercent(selectedSignal.signal.confidence_score)} />
                <Detail label="Timeframe" value={selectedSignal.signal.timeframe} />
                <Detail label="Created" value={formatDateTime(selectedSignal.signal.created_at)} />
              </dl>
              {data.selectedReadiness && (
                <div className="mt-5 rounded-lg border border-[var(--line)] p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      value={data.selectedReadiness.assessment.readiness_label}
                      tone={toneForQuality(data.selectedReadiness.assessment.readiness_label)}
                    />
                    <span className="text-sm font-medium text-slate-500">
                      Quality status {formatPercent(data.selectedReadiness.assessment.readiness_score)}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                    {data.selectedReadiness.assessment.summary}
                  </p>
                </div>
              )}
            </AnimatedListItem>
            <AnimatedListItem
              as="section"
              className={`${motionCardClass} muted-surface rounded-lg p-4`}
              preset="scale-subtle"
              style={motionRevealDensityStyle(1, "compact")}
            >
              <h3 className="mb-3 text-sm font-semibold uppercase text-slate-500">Key evidence</h3>
              <EvidenceList evidence={selectedSignal.evidence.slice(0, 6)} />
            </AnimatedListItem>
            <AnimatedListItem
              as="section"
              className={`${motionCardClass} muted-surface rounded-lg p-4`}
              preset="scale-subtle"
              style={motionRevealDensityStyle(2, "compact")}
            >
              <h3 className="mb-3 text-sm font-semibold uppercase text-slate-500">Outcome history</h3>
              <OutcomeList outcomes={data.selectedOutcomes} />
            </AnimatedListItem>
            <AnimatedListItem
              as="section"
              className={`${motionCardClass} muted-surface rounded-lg p-4`}
              preset="scale-subtle"
              style={motionRevealDensityStyle(3, "compact")}
            >
              <h3 className="mb-3 text-sm font-semibold uppercase text-slate-500">Setup context</h3>
              <SetupContextPanel setupContext={data.selectedSetupContext} />
            </AnimatedListItem>
          </div>
          <aside className="space-y-5">
            <div>
              <h3 className="mb-3 text-sm font-semibold uppercase text-slate-500">Confidence components</h3>
              <ConfidenceList components={selectedSignal.confidence_components} />
            </div>
            <div>
              <h3 className="mb-3 text-sm font-semibold uppercase text-slate-500">Risk notes</h3>
              <RiskNoteList notes={selectedSignal.risk_notes} />
            </div>
            {data.selectedReadiness?.next_steps?.length ? (
              <div>
                <h3 className="mb-3 text-sm font-semibold uppercase text-slate-500">Action plan items</h3>
                <ul className="space-y-2">
                  {data.selectedReadiness.next_steps.map((item, index) => (
                    <AnimatedListItem
                      as="li"
                      key={item}
                      className={`${motionCardClass} muted-surface rounded-lg p-3`}
                      preset="scale-subtle"
                      style={motionRevealDensityStyle(index, "compact")}
                    >
                      {item}
                    </AnimatedListItem>
                  ))}
                </ul>
              </div>
            ) : null}
          </aside>
        </div>
      )}
    </Panel>
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
