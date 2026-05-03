import { EmptyState } from "@/components/empty-states/empty-state";
import { EvidenceList } from "@/components/evidence/evidence-list";
import { Panel } from "@/components/layout/panel";
import { OutcomeList } from "@/components/outcomes/outcome-list";
import { ConfidenceList } from "@/components/signals/confidence-list";
import { JsonSection } from "@/components/signals/json-section";
import { RiskNoteList } from "@/components/signals/risk-note-list";
import { SetupContextPanel } from "@/components/signals/setup-context-panel";
import { Badge, toneForBias, toneForQuality } from "@/components/status/badge";
import type {
  AuditTimeline,
  ContextRead,
  DecisionReadinessAssessmentResponse,
  IntelligenceReport,
  SetupContext,
  SignalClassification,
  SignalOutcome,
} from "@/lib/api/types";
import { formatDateTime } from "@/lib/formatting/dates";
import { humanizeLabel } from "@/lib/formatting/labels";
import { formatPercent } from "@/lib/formatting/numbers";

type SignalDetailViewProps = {
  signal: SignalClassification | null;
  report: IntelligenceReport | null;
  outcomes: SignalOutcome[];
  readiness: DecisionReadinessAssessmentResponse | null;
  marketRegime: ContextRead | null;
  marketSession: ContextRead | null;
  auditTimeline: AuditTimeline | null;
  setupContext: SetupContext | null;
};

export function SignalDetailView({
  signal,
  report,
  outcomes,
  readiness,
  marketRegime,
  marketSession,
  auditTimeline,
  setupContext,
}: SignalDetailViewProps) {
  if (!signal && !report) {
    return <EmptyState title="Signal not available" message="The API did not return a signal or report for this identifier." />;
  }

  return (
    <div className="space-y-6">
      {signal && (
        <Panel title="Summary" eyebrow="Read-only signal detail">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-[var(--strong)]">{humanizeLabel(signal.signal.bias)}</h2>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                {signal.signal.summary || signal.signal.no_signal_reason || "No signal summary returned."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge value={signal.signal.bias} tone={toneForBias(signal.signal.bias)} />
              <Badge value={signal.signal.confidence_label} tone={toneForQuality(signal.signal.confidence_label)} />
              <Badge value={signal.signal.pattern_type || "No pattern"} tone="info" />
            </div>
          </div>
          <dl className="mt-5 grid gap-4 text-sm md:grid-cols-4">
            <Detail label="Confidence" value={formatPercent(signal.signal.confidence_score)} />
            <Detail label="Timeframe" value={signal.signal.timeframe} />
            <Detail label="Status" value={humanizeLabel(signal.signal.classification_status)} />
            <Detail label="Created" value={formatDateTime(signal.signal.created_at)} />
          </dl>
        </Panel>
      )}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          {signal && (
            <>
              <Panel title="Evidence" eyebrow="Deterministic inputs">
                <EvidenceList evidence={signal.evidence} />
              </Panel>
              <Panel title="Confidence" eyebrow="Component scoring">
                <ConfidenceList components={signal.confidence_components} />
              </Panel>
              <Panel title="Risk" eyebrow="Context notes">
                <RiskNoteList notes={signal.risk_notes} />
              </Panel>
              <Panel title="Outcomes" eyebrow="Observed horizons">
                <OutcomeList outcomes={outcomes} />
              </Panel>
              <Panel title="Setup Context" eyebrow="Non-advisory context">
                <SetupContextPanel setupContext={setupContext} />
              </Panel>
            </>
          )}
          {report && (
            <Panel title="Intelligence Report" eyebrow="Report sections">
              <JsonSection value={report.sections} />
              {report.missing_sections.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {report.missing_sections.map((section) => (
                    <Badge key={section} value={`${section} missing`} tone="warning" />
                  ))}
                </div>
              )}
            </Panel>
          )}
        </div>
        <aside className="space-y-6">
          <Panel title="Readiness" eyebrow="Quality status">
            {readiness ? (
              <div>
                <div className="flex flex-wrap gap-2">
                  <Badge value={readiness.assessment.readiness_label} tone={toneForQuality(readiness.assessment.readiness_label)} />
                  <Badge value={formatPercent(readiness.assessment.readiness_score)} tone="info" />
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{readiness.assessment.summary}</p>
                {readiness.next_steps.length > 0 && (
                  <ul className="mt-4 space-y-2">
                    {readiness.next_steps.map((step) => (
                      <li key={step} className="muted-surface rounded-lg p-3 text-sm">
                        {step}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <EmptyState title="Readiness hidden" message="No readiness endpoint response was available for this signal." />
            )}
          </Panel>
          <Panel title="Market Context" eyebrow="Regime and session">
            <div className="flex flex-wrap gap-2">
              <Badge value={contextLabel(marketRegime, "regime_label")} tone="info" />
              <Badge value={contextLabel(marketSession, "session_label")} tone="info" />
            </div>
          </Panel>
          <Panel title="Audit Timeline" eyebrow="Traceability">
            {auditTimeline ? (
              <div>
                <Badge value={`Completeness ${formatPercent(auditTimeline.completeness_score)}`} tone="info" />
                <p className="mt-3 text-sm text-slate-500">{auditTimeline.events.length} timeline events returned.</p>
              </div>
            ) : (
              <EmptyState title="Audit timeline unavailable" message="The timeline endpoint did not return data for this signal." />
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

function contextLabel(context: ContextRead | null, key: "regime_label" | "session_label"): string {
  if (!context) {
    return "Not available";
  }
  const value = context[key] || context.label;
  return typeof value === "string" ? value : "Not available";
}
