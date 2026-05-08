import { formatDateTime } from "@/lib/formatting/dates";
import { formatInteger } from "@/lib/formatting/numbers";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import { navigationHref } from "@/lib/ui/navigation";
import { toneForBias, toneForDataQuality, toneForOutcome, toneForPriority } from "@/lib/ui/statusStyles";
import { cn } from "@/lib/ui/cn";
import { motionCardClass, motionRevealClass, motionRevealDensityStyle } from "@/lib/ui/motion";
import type {
  BriefActiveSetupItem,
  BriefAvoidConditionItem,
  BriefDataQualityIssue,
  BriefOutcomeUpdateItem,
  BriefPendingActionItem,
  BriefReviewNeededItem,
  BriefWatchNextItem,
  WorkspaceBrief,
} from "@/lib/brief/types";
import {
  BriefBadge,
  BriefEmptyBlock,
  BriefMetric,
  BriefPanel,
  BriefTextLink,
} from "./BriefNarrativePrimitives";

export function BriefNarrative({ brief }: { brief: WorkspaceBrief }) {
  return (
    <div className={cn("space-y-6", motionRevealClass("scale"))}>
      <BriefHero brief={brief} />
      {brief.backendUnavailable && (
        <BriefPanel
          title="Backend unavailable"
          eyebrow="Brief state"
          className={motionRevealClass()}
          style={motionRevealDensityStyle(1)}
        >
          <BriefEmptyBlock
            title="Backend unavailable"
            message="The brief is limited to any optional endpoint responses that were returned before the backend became unavailable."
          />
        </BriefPanel>
      )}
      {!brief.workspace && (
        <BriefPanel
          title="No workspace available"
          eyebrow="Empty state"
          className={motionRevealClass()}
          style={motionRevealDensityStyle(2)}
        >
          <BriefEmptyBlock
            title="No workspace available"
            message="Create or seed a workspace before a structured daily brief can be generated."
          />
        </BriefPanel>
      )}
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
        <div className="space-y-6">
          <WhatChangedSection brief={brief} />
          <ReviewFirstSection items={brief.activeSetups} />
          <FreshSymbolsSection brief={brief} />
          <OutcomeReadySection items={brief.outcomeUpdates} />
        </div>
        <aside className="space-y-6">
          <NeedsConfirmationSection items={brief.reviewNeeded} />
          <AvoidConditionsSection items={brief.avoidConditions} />
          <WatchNextSection items={brief.watchNext} />
          <PendingActionsSection items={brief.pendingActions} />
        </aside>
      </section>
      <DataQualitySection items={brief.dataQualityIssues} workspaceId={brief.workspace?.id || null} />
    </div>
  );
}

function BriefHero({ brief }: { brief: WorkspaceBrief }) {
  const period = periodLabel(brief);
  const watchlist = brief.watchlistId ? `Watchlist ${shortIdentifier(brief.watchlistId)}` : "Workspace filter";
  return (
    <section
      className={cn(
        "rounded-3xl border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.18),transparent_34%),linear-gradient(135deg,#ffffff,rgba(240,253,250,0.95)_46%,rgba(239,246,255,0.95))] p-5 shadow-[0_30px_100px_rgba(15,23,42,0.10)] dark:border-slate-800 dark:bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.16),transparent_34%),linear-gradient(135deg,#020617,#0f172a_52%,#082f49)] sm:p-7",
        motionRevealClass(),
      )}
    >
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2">
            <BriefBadge tone="info">{brief.sourceLabel}</BriefBadge>
            <BriefBadge tone={brief.backendUnavailable ? "danger" : "good"}>{brief.backendUnavailable ? "Backend unavailable" : "Brief data loaded"}</BriefBadge>
            <BriefBadge tone="neutral">{watchlist}</BriefBadge>
          </div>
          <p className="mt-6 text-sm font-semibold uppercase text-slate-500 dark:text-slate-400">Daily Brief</p>
          <h1 className="mt-2 max-w-4xl text-4xl font-semibold text-slate-950 dark:text-white sm:text-5xl">
            {brief.workspace?.name || brief.appName}
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
            Structured narrative context for what changed, fresh symbols, review-first setup context, confirmation needs, avoid conditions, observed outcomes, and backend-safe follow-up.
          </p>
        </div>
        <div className="min-w-[280px] rounded-3xl border border-white/80 bg-white/80 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur dark:border-slate-700 dark:bg-slate-950/65">
          <p className="text-xs font-semibold uppercase text-slate-500">Period</p>
          <p className="mt-2 text-xl font-semibold text-[var(--strong)]">{period}</p>
          <p className="mt-2 text-sm text-slate-500">Generated {formatDateTime(brief.generatedAt)}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <BriefTextLink href={navigationHref("commandCenter", brief.workspace?.id)}>Open command center</BriefTextLink>
            <BriefTextLink href={navigationHref("triage", brief.workspace?.id)}>Open triage</BriefTextLink>
          </div>
        </div>
      </div>
      <div className="mt-7 grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
        <BriefMetric label="Symbols reviewed" value={formatInteger(brief.summary.totalSymbolsReviewed)} detail="Brief focus rows" />
        <BriefMetric label="Fresh symbols" value={formatInteger(brief.summary.freshSymbols)} detail="Data fresh" />
        <BriefMetric label="Stale/degraded" value={formatInteger(brief.summary.staleOrDegradedSymbols)} detail="Review recommended" />
        <BriefMetric label="Review first" value={formatInteger(brief.summary.activeSetupCount)} detail="Setup context" />
        <BriefMetric label="Needs review" value={formatInteger(brief.summary.reviewRecommendedCount)} detail="Confirmation or avoid" />
        <BriefMetric label="Outcomes ready" value={formatInteger(brief.summary.recentOutcomeUpdateCount)} detail="Observed horizons" />
        <BriefMetric label="Pending actions" value={formatInteger(brief.summary.pendingBackendActionCount)} detail="Backend-safe" />
      </div>
    </section>
  );
}

function WhatChangedSection({ brief }: { brief: WorkspaceBrief }) {
  const items = [
    ...brief.digestSummaries.slice(0, 4).map((item) => ({
      id: `digest:${item.id}`,
      title: item.title,
      detail: item.summary,
      tone: toneForPriority(item.priority),
      href: item.signalId ? `/signals/${item.signalId}` : navigationHref("brief", brief.workspace?.id),
      label: humanizeLabel(item.itemType),
    })),
    ...brief.outcomeUpdates.slice(0, 2).map((item) => ({
      id: `outcome:${item.id}`,
      title: `${item.symbol} ${item.timeframe}`,
      detail: item.safeSummary,
      tone: toneForOutcome(item.outcomeLabel),
      href: `/signals/${item.signalId}`,
      label: item.observationLabel,
    })),
    ...brief.dataQualityIssues.slice(0, 2).map((item) => ({
      id: `data:${item.id}`,
      title: `${item.symbol}${item.timeframe ? ` ${item.timeframe}` : ""}`,
      detail: item.detail,
      tone: toneForDataQuality(item.severity),
      href: navigationHref("dataOnboarding", brief.workspace?.id),
      label: humanizeLabel(item.label),
    })),
  ].slice(0, 8);
  return (
    <BriefPanel title="What Changed" eyebrow="Digest" className={motionRevealClass()} style={motionRevealDensityStyle(3)}>
      {items.length === 0 ? (
        <BriefEmptyBlock title="No brief generated" message="No backend brief items or fallback digest rows were returned for this workspace." />
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => (
            <a
              key={item.id}
              href={item.href}
              className={cn(
                "block rounded-2xl border border-slate-200 bg-slate-50/70 p-4 transition hover:bg-white dark:border-slate-800 dark:bg-slate-900/45",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="font-semibold text-[var(--strong)]">{item.title}</p>
                <BriefBadge tone={item.tone}>{item.label}</BriefBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function FreshSymbolsSection({ brief }: { brief: WorkspaceBrief }) {
  const freshItems = brief.marketFocus.filter((item) => item.freshnessLabel === "fresh").slice(0, 8);
  return (
    <BriefPanel title="Fresh Symbols" eyebrow="Data fresh" className={motionRevealClass()} style={motionRevealDensityStyle(4)}>
      {freshItems.length === 0 ? (
        <BriefEmptyBlock title="No fresh data" message="No fresh market-memory rows were returned for the current brief scope." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {freshItems.map((item, index) => (
            <a
              key={item.id}
              href={`/symbols/${item.symbolId}`}
              className={cn(
                "rounded-2xl border border-emerald-200 bg-emerald-50/65 p-4 transition hover:bg-white dark:border-emerald-900 dark:bg-emerald-950/25",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.timeframe}</p>
                </div>
                <BriefBadge tone={toneForBias(item.latestBias)}>{item.latestBias}</BriefBadge>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <BriefBadge tone={toneForDataQuality(item.confidenceLabel)}>{item.confidenceLabel}</BriefBadge>
                <BriefBadge tone={toneForDataQuality(item.dataQualityLabel)}>{item.dataQualityLabel}</BriefBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.topWarning}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function ReviewFirstSection({ items }: { items: BriefActiveSetupItem[] }) {
  return (
    <BriefPanel title="Review-First Setups" eyebrow="Setup context" className={motionRevealClass()} style={motionRevealDensityStyle(5)}>
      {items.length === 0 ? (
        <BriefEmptyBlock title="No setups" message="No directional setup context was available in the current brief." />
      ) : (
        <div className="space-y-3">
          {items.slice(0, 8).map((item, index) => (
            <a
              key={item.signalId}
              href={item.reviewLink}
              className={cn(
                "block rounded-2xl border border-slate-200 bg-white/70 p-4 transition hover:bg-teal-50/70 dark:border-slate-800 dark:bg-slate-950/45 dark:hover:bg-teal-950/20",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol} {item.timeframe}</p>
                  <p className="mt-1 text-sm text-slate-500">{humanizeLabel(item.patternType)}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <BriefBadge tone={toneForBias(item.bias)}>{item.bias}</BriefBadge>
                  <BriefBadge tone={toneForDataQuality(item.setupQualityLabel)}>{item.setupQualityLabel}</BriefBadge>
                </div>
              </div>
              <div className="mt-3 space-y-2">
                {item.keyEvidence.slice(0, 3).map((evidence) => (
                  <p key={evidence} className="text-sm leading-6 text-slate-600 dark:text-slate-300">{evidence}</p>
                ))}
              </div>
              <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
                <BriefDetail label="Invalidation context" value={item.invalidationContext || "Not available"} />
                <BriefDetail label="Observation context" value={item.waitCondition || "Review first"} />
              </div>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function NeedsConfirmationSection({ items }: { items: BriefReviewNeededItem[] }) {
  return (
    <BriefPanel title="Needs Confirmation" eyebrow="Review queue" className={motionRevealClass()} style={motionRevealDensityStyle(6)}>
      {items.length === 0 ? (
        <BriefEmptyBlock title="No confirmation items" message="No open review or readiness confirmation items were returned." />
      ) : (
        <div className="space-y-3">
          {items.slice(0, 8).map((item, index) => (
            <a
              key={item.id}
              href={item.signalId ? `/signals/${item.signalId}` : "#"}
              className={cn(
                "block rounded-2xl border border-amber-200 bg-amber-50/65 p-4 dark:border-amber-900 dark:bg-amber-950/25",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="font-semibold text-[var(--strong)]">{item.label}</p>
                <BriefBadge tone={toneForPriority(item.priority)}>{humanizeLabel(item.priority)}</BriefBadge>
              </div>
              <p className="mt-2 text-sm text-slate-500">{item.source}</p>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function AvoidConditionsSection({ items }: { items: BriefAvoidConditionItem[] }) {
  return (
    <BriefPanel title="Avoid Conditions" eyebrow="Constraints" className={motionRevealClass()} style={motionRevealDensityStyle(7)}>
      {items.length === 0 ? (
        <BriefEmptyBlock title="No avoid conditions" message="No stale, conflicting, low-quality, or unresolved review constraints were returned." />
      ) : (
        <div className="space-y-3">
          {items.slice(0, 8).map((item, index) => (
            <a
              key={item.id}
              href={item.signalId ? `/signals/${item.signalId}` : "#"}
              className={cn(
                "block rounded-2xl border border-slate-200 bg-slate-50/75 p-4 dark:border-slate-800 dark:bg-slate-900/50",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.condition}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.symbol}{item.timeframe ? ` ${item.timeframe}` : ""}</p>
                </div>
                <BriefBadge tone={toneForPriority(item.severity)}>{humanizeLabel(item.severity)}</BriefBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function OutcomeReadySection({ items }: { items: BriefOutcomeUpdateItem[] }) {
  return (
    <BriefPanel title="Outcomes Ready" eyebrow="Observed behavior" className={motionRevealClass()} style={motionRevealDensityStyle(8)}>
      {items.length === 0 ? (
        <BriefEmptyBlock title="No outcomes ready" message="No recent observed outcome horizons were returned for the current brief." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {items.slice(0, 8).map((item, index) => (
            <a
              key={item.id}
              href={`/signals/${item.signalId}`}
              className={cn(
                "rounded-2xl border border-sky-200 bg-sky-50/65 p-4 transition hover:bg-white dark:border-sky-900 dark:bg-sky-950/25",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol} {item.timeframe}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.horizon}</p>
                </div>
                <BriefBadge tone={toneForOutcome(item.outcomeLabel)}>{item.observationLabel}</BriefBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.safeSummary}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function WatchNextSection({ items }: { items: BriefWatchNextItem[] }) {
  return (
    <BriefPanel title="Watch Next" eyebrow="Observation zones" className={motionRevealClass()} style={motionRevealDensityStyle(9)}>
      {items.length === 0 ? (
        <BriefEmptyBlock title="No watch-next rows" message="Setup context did not return next observations or observation zones." />
      ) : (
        <div className="space-y-3">
          {items.slice(0, 8).map((item, index) => (
            <a
              key={item.id}
              href={item.signalId ? `/signals/${item.signalId}` : "#"}
              className={cn(
                "block rounded-2xl border border-slate-200 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/45",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="font-semibold text-[var(--strong)]">{item.symbol} {item.timeframe}</p>
                <BriefBadge tone="info">Observation zone</BriefBadge>
              </div>
              <p className="mt-3 text-sm font-semibold text-[var(--strong)]">{item.observation}</p>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function PendingActionsSection({ items }: { items: BriefPendingActionItem[] }) {
  return (
    <BriefPanel
      title="Pending Backend-Safe Actions"
      eyebrow="Follow-up"
      className={motionRevealClass()}
      style={motionRevealDensityStyle(10)}
    >
      {items.length === 0 ? (
        <BriefEmptyBlock title="No pending actions" message="No due backend-safe action items were returned." />
      ) : (
        <div className="space-y-3">
          {items.slice(0, 8).map((item, index) => (
            <div
              key={item.id}
              className={cn(
                "rounded-2xl border border-slate-200 bg-slate-50/75 p-4 dark:border-slate-800 dark:bg-slate-900/50",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="font-semibold text-[var(--strong)]">{item.safeLabel}</p>
                <BriefBadge tone={toneForDataQuality(item.status)}>{humanizeLabel(item.status)}</BriefBadge>
              </div>
              <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                <BriefDetail label="Source" value={item.source} />
                <BriefDetail label="Due" value={formatDateTime(item.dueTime)} />
              </div>
            </div>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function DataQualitySection({ items, workspaceId }: { items: BriefDataQualityIssue[]; workspaceId: string | null }) {
  return (
    <BriefPanel
      title="Data Quality and Recovery Context"
      eyebrow="Reliability"
      className={motionRevealClass()}
      style={motionRevealDensityStyle(11)}
    >
      {items.length === 0 ? (
        <BriefEmptyBlock title="No data-quality issues" message="No freshness, gap, provider, or setup-quality issues were returned." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.slice(0, 9).map((item, index) => (
            <a
              key={item.id}
              href={navigationHref("dataOnboarding", workspaceId)}
              className={cn(
                "rounded-2xl border border-slate-200 bg-slate-50/75 p-4 transition hover:bg-white dark:border-slate-800 dark:bg-slate-900/50",
                motionCardClass,
                motionRevealClass(),
              )}
              style={motionRevealDensityStyle(index, "compact")}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{humanizeLabel(item.label)}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.symbol}{item.timeframe ? ` ${item.timeframe}` : ""}</p>
                </div>
                <BriefBadge tone={toneForDataQuality(item.severity)}>{humanizeLabel(item.severity)}</BriefBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </a>
          ))}
        </div>
      )}
    </BriefPanel>
  );
}

function BriefDetail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-[var(--strong)]">{value}</dd>
    </div>
  );
}

function periodLabel(brief: WorkspaceBrief): string {
  if (brief.periodStart && brief.periodEnd) {
    return `${formatDateTime(brief.periodStart)} to ${formatDateTime(brief.periodEnd)}${brief.timezone ? ` ${brief.timezone}` : ""}`;
  }
  return `Generated ${formatDateTime(brief.generatedAt)}`;
}
