import { Panel } from "@/components/layout/panel";
import { Badge } from "@/components/status/badge";
import { diagnosticTone, reviewLabel } from "@/lib/review/labels";
import type { OutcomeReviewData } from "@/lib/review/types";
import type { ReactNode } from "react";

export function ProfileReliabilityPanel({ data }: { data: OutcomeReviewData }) {
  const profileDiagnostics = data.profileDiagnostics.slice(0, 4);
  const calibrationBins = data.calibrationBins.slice(0, 4);
  const driftResults = data.cohortDrift.slice(0, 4);
  if (profileDiagnostics.length === 0 && calibrationBins.length === 0 && driftResults.length === 0) {
    return null;
  }
  return (
    <Panel title="Profile reliability" eyebrow="Calibration and drift">
      <div className="grid gap-4 xl:grid-cols-3">
        <Section title="Profile diagnostics">
          {profileDiagnostics.length === 0 ? (
            <EmptyLine message="No profile diagnostics returned." />
          ) : (
            profileDiagnostics.map((item) => (
              <ReliabilityItem
                key={item.id}
                title={item.strategy_profile_key}
                label={item.diagnostic_label}
                detail={`${item.evaluated_count} evaluated outcomes · ${item.horizon_minutes} minute horizon`}
                summary={item.diagnostic_summary}
              />
            ))
          )}
        </Section>
        <Section title="Confidence calibration">
          {calibrationBins.length === 0 ? (
            <EmptyLine message={data.calibrationRun?.summary || "No calibration bins returned."} />
          ) : (
            calibrationBins.map((item) => (
              <ReliabilityItem
                key={item.id}
                title={item.bin_label}
                label={item.calibration_label}
                detail={`${item.evaluated_count} evaluated outcomes · ${item.horizon_minutes} minute horizon`}
                summary={`Average confidence ${formatPercent(item.average_confidence_score)} · alignment ${formatPercent(item.confidence_alignment_score)}`}
              />
            ))
          )}
        </Section>
        <Section title="Cohort drift">
          {driftResults.length === 0 ? (
            <EmptyLine message="No cohort drift results returned." />
          ) : (
            driftResults.map((item) => (
              <ReliabilityItem
                key={item.id}
                title={reviewLabel(item.cohort_key)}
                label={item.severity || item.drift_label}
                detail={`${item.baseline_sample_size} baseline · ${item.comparison_sample_size} recent`}
                summary={item.summary}
              />
            ))
          )}
        </Section>
      </div>
    </Panel>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold text-[var(--strong)]">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function ReliabilityItem({ title, label, detail, summary }: { title: string; label: string; detail: string; summary: string }) {
  return (
    <div className="muted-surface rounded-lg p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-sm font-semibold text-[var(--strong)]">{title}</h4>
        <Badge value={label} tone={diagnosticTone(label)} />
      </div>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{summary}</p>
      <p className="mt-2 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

function EmptyLine({ message }: { message: string }) {
  return <p className="text-sm leading-6 text-slate-500">{message}</p>;
}

function formatPercent(value: string | null | undefined): string {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "not available";
  }
  return `${Math.round(parsed * 100)}%`;
}
