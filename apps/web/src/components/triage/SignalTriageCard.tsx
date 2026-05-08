import type { CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";
import { Badge } from "@/components/status/badge";
import { BiasBadge } from "@/components/status/BiasBadge";
import { ConfidenceBadge } from "@/components/status/ConfidenceBadge";
import { FreshnessBadge } from "@/components/status/FreshnessBadge";
import { DataQualityBadge } from "@/components/status/DataQualityBadge";
import { OutcomeLabelBadge } from "@/components/status/OutcomeLabelBadge";
import { SetupQualityBadge } from "@/components/status/SetupQualityBadge";
import { ButtonLink } from "@/components/ui/Button";
import { workflowHref } from "@/components/layout/workflow-links";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import { formatPercent } from "@/lib/formatting/numbers";
import { safeTriageText, shortReason } from "@/lib/triage/labels";
import type { TriageCandidate } from "@/lib/triage/types";
import { MOTION_INTERACTIVE_CLASS, motionCardClass, motionRevealPresetClass, motionRevealDensityStyle } from "@/lib/ui/motion";
import { TriageReasonBadges } from "./TriageReasonBadges";

export function SignalTriageCard({
  candidate,
  className = "",
  style = motionRevealDensityStyle(),
}: {
  candidate: TriageCandidate;
  className?: string;
  style?: CSSProperties;
}) {
  const signal = candidate.signal.signal;
  const symbolLabel = candidate.symbol?.symbol || shortIdentifier(signal.symbol_id);
  const evidenceCount = candidate.signal.evidence.length;
  const conflictingEvidenceCount = candidate.signal.evidence.filter((item) =>
    ["conflict", "opposes", "opposing", "mixed"].includes(item.direction),
  ).length;
  const latestOutcome = candidate.outcomes[0] || null;
  const topEvidence = candidate.signal.evidence[0]?.message || candidate.signal.signal.summary;
  const topRisk = candidate.signal.risk_notes[0]?.message || candidate.setupContext?.risk_notes_json[0]?.message;
  const setupQuality = candidate.setupContext?.setup_quality_label || "Context unavailable";
  const workspaceId = signal.workspace_id;
  const dataOnboardingBaseHref = workflowHref("dataOnboarding", workspaceId);
  const dataOnboardingHref = `${dataOnboardingBaseHref}${dataOnboardingBaseHref.includes("?") ? "&" : "?"}symbolIds=${signal.symbol_id}&timeframes=${encodeURIComponent(signal.timeframe)}`;

  return (
    <article
      style={style}
      className={cn(
        "group rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-[0_1px_0_rgba(15,23,42,0.04)] transition hover:border-[var(--accent)] hover:shadow-soft",
        motionCardClass,
        motionRevealPresetClass(),
        MOTION_INTERACTIVE_CLASS,
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold text-[var(--strong)]">{symbolLabel}</h3>
          <p className="mt-1 text-xs font-medium uppercase text-slate-500">
            {signal.timeframe} / {humanizeLabel(signal.pattern_type || "No pattern")}
          </p>
        </div>
        <Badge value={candidate.classification.mainReason.label} tone={candidate.classification.mainReason.tone} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <BiasBadge value={signal.bias} />
        <ConfidenceBadge value={signal.confidence_label} />
        <SetupQualityBadge value={setupQuality} />
        {latestOutcome && <OutcomeLabelBadge value={latestOutcome.outcome_label} />}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <Detail label="Confidence" value={formatPercent(signal.confidence_score)} featured />
        {candidate.priorityScore && (
          <Detail label="Priority score" value={formatPercent(candidate.priorityScore.priority_score)} featured />
        )}
        <Detail label="Setup quality" value={formatPercent(candidate.setupContext?.setup_quality_score)} />
        <Detail label="Freshness" value={formatRelativeTime(candidate.memory?.latest_final_candle_time)} />
        <DetailBadge label="Freshness"><FreshnessBadge value={candidate.memory?.freshness_label || "Missing market memory"} /></DetailBadge>
        <DetailBadge label="Data quality"><DataQualityBadge value={candidate.memory?.data_quality_label || "Unknown"} /></DetailBadge>
      </dl>
      <div className="mt-4 grid grid-cols-3 gap-2">
        <MiniStat label="Evidence" value={String(evidenceCount)} />
        <MiniStat label="Conflicts" value={String(conflictingEvidenceCount)} />
        <MiniStat label="Outcomes" value={String(candidate.outcomes.length)} />
      </div>
      <div className="mt-4 space-y-3">
        <TextBlock label="Top reason" value={topEvidence} fallback="No evidence summary returned." />
        <TextBlock label="Top risk note" value={topRisk} fallback="No risk note returned." />
      </div>
      <div className="mt-4">
        <TriageReasonBadges reasons={candidate.classification.reasons} />
      </div>
      {candidate.missingContexts.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {candidate.missingContexts.slice(0, 4).map((context) => (
            <Badge key={context} value={`${context} missing`} tone="neutral" />
          ))}
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2 text-sm font-medium">
        <ButtonLink href={`/signals/${signal.id}`} className="w-full justify-center">
          Review setup
        </ButtonLink>
        {candidate.setupContext && (
          <ButtonLink href={`/signals/${signal.id}#setup-context`}>
            Setup context
          </ButtonLink>
        )}
        {candidate.classification.column === "stale_data_issue" && (
          <ButtonLink href={dataOnboardingHref}>
            Data onboarding
          </ButtonLink>
        )}
      </div>
      <p className="mt-3 text-xs text-slate-500">Stored {formatDateTime(signal.created_at)}</p>
    </article>
  );
}

function Detail({ label, value, featured = false }: { label: string; value: string; featured?: boolean }) {
  return (
    <div className={`rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3 ${featured ? "col-span-1" : ""}`}>
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 truncate text-sm font-semibold text-[var(--strong)]">{value}</dd>
    </div>
  );
}

function DetailBadge({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--panel-muted)] p-3">
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 flex">{children}</dd>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-[var(--line)] px-2 py-2 text-center">
      <p className="text-sm font-semibold text-[var(--strong)]">{value}</p>
      <p className="mt-0.5 truncate text-[10px] font-semibold uppercase text-slate-500">{label}</p>
    </div>
  );
}

function TextBlock({ label, value, fallback }: { label: string; value: unknown; fallback: string }) {
  const text = typeof value === "string" ? value : null;
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{shortReason(safeTriageText(text, fallback))}</p>
    </div>
  );
}
