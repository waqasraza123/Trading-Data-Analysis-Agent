import type { ReactNode } from "react";
import { Badge } from "@/components/status/badge";
import { BiasBadge } from "@/components/status/BiasBadge";
import { ConfidenceBadge } from "@/components/status/ConfidenceBadge";
import { FreshnessBadge } from "@/components/status/FreshnessBadge";
import { DataQualityBadge } from "@/components/status/DataQualityBadge";
import { SetupQualityBadge } from "@/components/status/SetupQualityBadge";
import { ButtonLink } from "@/components/ui/Button";
import { workflowHref } from "@/components/layout/workflow-links";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import { formatPercent } from "@/lib/formatting/numbers";
import { safeTriageText, shortReason } from "@/lib/triage/labels";
import type { TriageCandidate } from "@/lib/triage/types";
import { TriageReasonBadges } from "./TriageReasonBadges";

export function SignalTriageCard({ candidate }: { candidate: TriageCandidate }) {
  const signal = candidate.signal.signal;
  const symbolLabel = candidate.symbol?.symbol || shortIdentifier(signal.symbol_id);
  const topEvidence = candidate.signal.evidence[0]?.message || candidate.signal.signal.summary;
  const topRisk = candidate.signal.risk_notes[0]?.message || candidate.setupContext?.risk_notes_json[0]?.message;
  const setupQuality = candidate.setupContext?.setup_quality_label || "Context unavailable";
  const workspaceId = signal.workspace_id;
  const dataOnboardingBaseHref = workflowHref("dataOnboarding", workspaceId);
  const dataOnboardingHref = `${dataOnboardingBaseHref}${dataOnboardingBaseHref.includes("?") ? "&" : "?"}symbolIds=${signal.symbol_id}&timeframes=${encodeURIComponent(signal.timeframe)}`;

  return (
    <article className="rounded-lg border border-[var(--line)] bg-[var(--panel)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-[var(--strong)]">{symbolLabel}</h3>
          <p className="mt-1 text-xs text-slate-500">
            {signal.timeframe} · {humanizeLabel(signal.pattern_type || "No pattern")}
          </p>
        </div>
        <Badge value={candidate.classification.mainReason.label} tone={candidate.classification.mainReason.tone} />
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <BiasBadge value={signal.bias} />
        <ConfidenceBadge value={signal.confidence_label} />
        <SetupQualityBadge value={setupQuality} />
      </div>
      <dl className="mt-4 grid gap-3 text-sm">
        <Detail label="Confidence" value={formatPercent(signal.confidence_score)} />
        {candidate.priorityScore && (
          <Detail label="Review priority" value={formatPercent(candidate.priorityScore.priority_score)} />
        )}
        <Detail label="Latest final candle" value={formatRelativeTime(candidate.memory?.latest_final_candle_time)} />
        <DetailBadge label="Freshness"><FreshnessBadge value={candidate.memory?.freshness_label || "Missing market memory"} /></DetailBadge>
        <DetailBadge label="Data quality"><DataQualityBadge value={candidate.memory?.data_quality_label || "Unknown"} /></DetailBadge>
      </dl>
      <div className="mt-4 space-y-3">
        <TextBlock label="Top evidence" value={topEvidence} fallback="No evidence summary returned." />
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
        <ButtonLink href={`/signals/${signal.id}`}>
          Signal detail
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
      <p className="mt-3 text-xs text-slate-500">Signal created {formatDateTime(signal.created_at)}</p>
    </article>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--line)] pb-2 last:border-b-0 last:pb-0">
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="text-right text-sm font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}

function DetailBadge({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-[var(--line)] pb-2 last:border-b-0 last:pb-0">
      <dt className="text-xs font-medium uppercase text-slate-500">{label}</dt>
      <dd className="flex justify-end">{children}</dd>
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
