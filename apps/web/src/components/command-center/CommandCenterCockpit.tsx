import Link from "next/link";
import { formatDateTime, formatRelativeTime } from "@/lib/formatting/dates";
import { formatInteger } from "@/lib/formatting/numbers";
import { humanizeLabel, shortIdentifier } from "@/lib/formatting/labels";
import { commandCenterHref, commandCenterLabel, commandCenterText, toneForState } from "@/lib/command-center/labels";
import type { CommandCenterData, CommandCenterTone } from "@/lib/command-center/types";
import { CommandCenterOverview } from "./CommandCenterOverview";
import { CommandCenterDailyScanButton } from "./CommandCenterDailyScanButton";
import {
  CockpitActionLink,
  CockpitBadge,
  CockpitEmptyState,
  CockpitMetric,
  CockpitPanel,
} from "./CommandCenterCockpitPrimitives";

export function CommandCenterCockpit({ data }: { data: CommandCenterData }) {
  const workspaceId = data.workspace?.id || null;
  return (
    <div className="space-y-6">
      <CommandCenterHero data={data} />
      {!data.workspace && (
        <CockpitEmptyState
          title="No workspace available"
          message="Create or seed a workspace before the daily cockpit can load market intelligence."
        />
      )}
      <CommandCenterBackendState data={data} />
      <CommandCenterOverview data={data} />
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(340px,0.7fr)]">
        <div className="space-y-6">
          <ReviewFirstPanel data={data} />
          <NeedsConfirmationStrip data={data} />
          <div className="grid gap-6 2xl:grid-cols-2">
            <AvoidConditionsPanel data={data} />
            <OutcomeReviewPanel data={data} />
          </div>
        </div>
        <aside className="space-y-6">
          <DataReliabilityPanel data={data} />
          <WorkflowProgressPanel data={data} />
          <NotificationsReviewPanel data={data} />
        </aside>
      </section>
      <DailyIntelligenceMap data={data} />
      <section className="rounded-3xl border border-slate-200/80 bg-slate-950 p-5 text-slate-100 shadow-[0_24px_80px_rgba(15,23,42,0.18)] dark:border-slate-800">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase text-slate-400">Daily workflow</p>
            <h2 className="mt-1 text-xl font-semibold">Continue the review loop</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
              Move from data readiness to deterministic scans, setup context, outcome review, and journal notes without execution or advisory steps.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <CockpitActionLink href={commandCenterHref("/brief", workspaceId)} tone="info">Open brief</CockpitActionLink>
            <CockpitActionLink href={commandCenterHref("/scanner", workspaceId)} tone="good">Open scanner</CockpitActionLink>
            <CockpitActionLink href={commandCenterHref("/review/outcomes", workspaceId)} tone="info">Review outcomes</CockpitActionLink>
          </div>
        </div>
      </section>
    </div>
  );
}

function CommandCenterHero({ data }: { data: CommandCenterData }) {
  const workspaceId = data.workspace?.id || null;
  const readiness = readinessLabel(data);
  const healthTone: CommandCenterTone = data.backendUnavailable ? "danger" : data.failures.length ? "warning" : "good";
  return (
    <section className="overflow-hidden rounded-3xl border border-white/70 bg-[radial-gradient(circle_at_top_left,rgba(20,184,166,0.20),transparent_34%),linear-gradient(135deg,#ffffff,rgba(240,249,255,0.95)_46%,rgba(236,253,245,0.92))] p-5 shadow-[0_30px_100px_rgba(15,23,42,0.11)] dark:border-slate-800 dark:bg-[radial-gradient(circle_at_top_left,rgba(45,212,191,0.18),transparent_34%),linear-gradient(135deg,#020617,#0f172a_52%,#0b2f2a)] sm:p-7">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2">
            <CockpitBadge tone="info">Daily market intelligence</CockpitBadge>
            <CockpitBadge tone={healthTone}>{data.backendUnavailable ? "Backend unavailable" : "Backend health checked"}</CockpitBadge>
            <CockpitBadge tone={readiness.tone}>{readiness.label}</CockpitBadge>
          </div>
          <p className="mt-6 text-sm font-semibold uppercase text-slate-500 dark:text-slate-400">Command Center</p>
          <h1 className="mt-2 max-w-4xl text-4xl font-semibold text-slate-950 dark:text-white sm:text-5xl">
            {data.workspace?.name || data.appName}
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600 dark:text-slate-300">
            A dense daily cockpit for data readiness, review-first setup context, confirmation queues, avoid conditions, observed outcomes, workflow progress, and backend-safe review items.
          </p>
        </div>
        <div className="min-w-[280px] rounded-3xl border border-white/80 bg-white/80 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.08)] backdrop-blur dark:border-slate-700 dark:bg-slate-950/65">
          <p className="text-xs font-semibold uppercase text-slate-500">Session context</p>
          <p className="mt-2 text-2xl font-semibold text-[var(--strong)]">{formatDateTime(data.generatedAt)}</p>
          <p className="mt-1 text-sm text-slate-500">Last refresh {formatRelativeTime(data.generatedAt)}</p>
          <div className="mt-4 grid gap-2">
            <CommandCenterDailyScanButton
              workspaceId={workspaceId}
              watchlistId={data.dailyWorkflowDefaultWatchlistId}
              preferenceProfileId={data.selectedPreferenceProfile?.id || null}
            />
            <div className="grid grid-cols-2 gap-2">
              <CockpitActionLink href={commandCenterHref("/command-center", workspaceId)} tone="neutral">Refresh data status</CockpitActionLink>
              <CockpitActionLink href={commandCenterHref("/data/onboarding", workspaceId)} tone="warning">Open data onboarding</CockpitActionLink>
              <CockpitActionLink href={commandCenterHref("/scanner", workspaceId)} tone="good">View scanner</CockpitActionLink>
              <CockpitActionLink href={commandCenterHref("/triage", workspaceId)} tone="info">View triage</CockpitActionLink>
            </div>
          </div>
        </div>
      </div>
      <div className="mt-7 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-7">
        <CockpitMetric label="Review first" value={formatInteger(data.summary.reviewFirstCount)} detail="Top context" tone="good" />
        <CockpitMetric label="Needs confirmation" value={formatInteger(data.summary.confirmationCount)} detail="Mixed or pending" tone="warning" />
        <CockpitMetric label="Data fresh" value={formatInteger(data.summary.freshSymbolCount)} detail="Fresh symbols" tone="good" />
        <CockpitMetric label="Data stale" value={formatInteger(data.summary.staleOrDegradedCount)} detail="Review recommended" tone="warning" />
        <CockpitMetric label="Outcomes ready" value={formatInteger(data.summary.outcomeReadyCount)} detail="Observed horizons" tone="info" />
        <CockpitMetric label="Unread items" value={formatInteger(data.summary.unreadNotificationCount)} detail="Inbox review" tone="info" />
        <CockpitMetric label="Blocked checks" value={formatInteger(data.latestProductReadiness?.blockers_json.length || 0)} detail="Readiness" tone={data.latestProductReadiness?.blockers_json.length ? "danger" : "neutral"} />
      </div>
    </section>
  );
}

function ReviewFirstPanel({ data }: { data: CommandCenterData }) {
  return (
    <CockpitPanel title="Review First" eyebrow="Priority setups">
      {data.reviewFirst.length === 0 ? (
        <CockpitEmptyState title="No review-first setups" message={data.sectionStatuses.reviewFirst.message} />
      ) : (
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white/70 dark:border-slate-800 dark:bg-slate-950/40">
          <div className="hidden grid-cols-[1.1fr_0.8fr_0.8fr_0.8fr_0.9fr_1.4fr_110px] gap-3 border-b border-slate-200 px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:border-slate-800 lg:grid">
            <span>Symbol</span>
            <span>Bias</span>
            <span>Confidence</span>
            <span>Priority</span>
            <span>Quality</span>
            <span>Main reason</span>
            <span>Detail</span>
          </div>
          <div className="divide-y divide-slate-200 dark:divide-slate-800">
            {data.reviewFirst.map((item) => (
              <Link
                key={item.signalId}
                href={item.href}
                className="grid gap-3 px-4 py-4 transition hover:bg-teal-50/60 dark:hover:bg-teal-950/20 lg:grid-cols-[1.1fr_0.8fr_0.8fr_0.8fr_0.9fr_1.4fr_110px] lg:items-center"
              >
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.timeframe}</p>
                </div>
                <CockpitBadge tone={toneForBias(item.bias)}>{item.bias}</CockpitBadge>
                <CockpitBadge tone={toneForState(item.confidenceLabel)}>{item.confidenceLabel}</CockpitBadge>
                <CockpitBadge tone="info">{item.reviewPriorityLabel || "Priority context"}</CockpitBadge>
                <div className="flex flex-wrap gap-2">
                  <CockpitBadge tone={toneForState(item.setupQualityLabel)}>{item.setupQualityLabel}</CockpitBadge>
                  <CockpitBadge tone={toneForState(item.freshnessLabel)}>{item.freshnessLabel}</CockpitBadge>
                </div>
                <p className="text-sm leading-6 text-slate-600 dark:text-slate-300">{item.mainReason}</p>
                <span className="text-sm font-semibold text-teal-700 dark:text-teal-300">Open setup</span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </CockpitPanel>
  );
}

function NeedsConfirmationStrip({ data }: { data: CommandCenterData }) {
  return (
    <CockpitPanel title="Needs Confirmation" eyebrow="Pending review context">
      {data.needsConfirmation.length === 0 ? (
        <CockpitEmptyState title="No confirmation queue" message={data.sectionStatuses.needsConfirmation.message} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
          {data.needsConfirmation.slice(0, 8).map((item) => (
            <Link key={item.id} href={item.href} className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 transition hover:-translate-y-0.5 hover:shadow-sm dark:border-amber-900 dark:bg-amber-950/35">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.timeframe}</p>
                </div>
                <CockpitBadge tone="warning">{item.label}</CockpitBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-700 dark:text-slate-300">{item.reason}</p>
            </Link>
          ))}
        </div>
      )}
    </CockpitPanel>
  );
}

function AvoidConditionsPanel({ data }: { data: CommandCenterData }) {
  return (
    <CockpitPanel title="Avoid Conditions" eyebrow="Risk filters">
      {data.avoidItems.length === 0 ? (
        <CockpitEmptyState title="No avoid conditions" message={data.sectionStatuses.avoidItems.message} />
      ) : (
        <div className="space-y-3">
          {data.avoidItems.slice(0, 6).map((item) => (
            <Link key={item.id} href={item.href} className="block rounded-2xl border border-slate-200 bg-slate-50/80 p-4 transition hover:bg-white dark:border-slate-800 dark:bg-slate-900/55 dark:hover:bg-slate-900">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.timeframe || "Workspace context"}</p>
                </div>
                <CockpitBadge tone={item.tone}>{item.condition}</CockpitBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
            </Link>
          ))}
        </div>
      )}
    </CockpitPanel>
  );
}

function DataReliabilityPanel({ data }: { data: CommandCenterData }) {
  const pollingSummary = providerPollingSummary(data);
  return (
    <CockpitPanel title="Data Reliability" eyebrow="Freshness and providers">
      <div className="grid grid-cols-2 gap-3">
        <CockpitMetric label="Fresh" value={formatInteger(data.summary.freshSymbolCount)} tone="good" />
        <CockpitMetric label="Stale" value={formatInteger(data.summary.staleOrDegradedCount)} tone="warning" />
        <CockpitMetric label="Missing candles" value={formatInteger(data.summary.missingCandleCount)} tone={data.summary.missingCandleCount ? "warning" : "neutral"} />
        <CockpitMetric label="Provider issues" value={formatInteger(data.summary.providerFailureCount)} tone={data.summary.providerFailureCount ? "danger" : "good"} />
      </div>
      <div className="mt-4 rounded-2xl border border-slate-200 bg-white/65 p-4 dark:border-slate-800 dark:bg-slate-950/40">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold text-[var(--strong)]">Provider health summary</p>
          <CockpitBadge tone={data.providerHealthSummary ? "info" : "neutral"}>{data.providerHealthSummary ? "Available" : "Not available"}</CockpitBadge>
        </div>
        <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
          {data.providerHealthSummary
            ? `${formatInteger(data.summary.dataReadyCount)} ready for deterministic analysis, ${formatInteger(data.summary.missingCandleCount)} missing candles, ${formatInteger(data.summary.providerFailureCount)} provider issues.`
            : data.sectionStatuses.dataReadiness.message}
        </p>
      </div>
      <div className="mt-4 grid gap-3">
        {data.dataReadiness.slice(0, 4).map((item) => (
          <Link key={item.id} href={item.href} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-3 transition hover:bg-white dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-[var(--strong)]">{item.symbol}</p>
                <p className="mt-1 text-xs text-slate-500">{item.timeframe || "All timeframes"}</p>
              </div>
              <CockpitBadge tone={item.tone}>{item.label}</CockpitBadge>
            </div>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
          </Link>
        ))}
      </div>
      <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50/70 p-4 text-sm dark:border-slate-800 dark:bg-slate-900/50">
        <p className="font-semibold text-[var(--strong)]">Provider polling</p>
        <p className="mt-2 leading-6 text-slate-600 dark:text-slate-300">{pollingSummary}</p>
      </div>
    </CockpitPanel>
  );
}

function OutcomeReviewPanel({ data }: { data: CommandCenterData }) {
  return (
    <CockpitPanel title="Outcome Review" eyebrow="Observed horizons">
      {data.outcomeReview.length === 0 ? (
        <CockpitEmptyState title="No outcomes ready" message={data.sectionStatuses.outcomeReview.message} />
      ) : (
        <div className="space-y-3">
          {data.outcomeReview.slice(0, 6).map((item) => (
            <Link key={item.id} href={item.href} className="block rounded-2xl border border-sky-200 bg-sky-50/70 p-4 transition hover:bg-white dark:border-sky-900 dark:bg-sky-950/30">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-[var(--strong)]">{item.symbol} {item.timeframe}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.horizon}</p>
                </div>
                <CockpitBadge tone="info">{item.observationLabel}</CockpitBadge>
              </div>
              <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
            </Link>
          ))}
        </div>
      )}
    </CockpitPanel>
  );
}

function WorkflowProgressPanel({ data }: { data: CommandCenterData }) {
  const run = data.selectedDailyWorkflowRun || data.dailyWorkflowRuns[0] || null;
  const steps = data.selectedDailyWorkflowSteps.length ? data.selectedDailyWorkflowSteps : [];
  const completed = steps.filter((step) => step.status === "completed").length;
  const skipped = steps.filter((step) => step.status === "skipped").length;
  const failed = steps.filter((step) => step.status === "failed").length;
  return (
    <CockpitPanel
      title="Workflow Progress"
      eyebrow="Latest daily run"
      action={<CommandCenterDailyScanButton workspaceId={data.workspace?.id || null} watchlistId={data.dailyWorkflowDefaultWatchlistId} preferenceProfileId={data.selectedPreferenceProfile?.id || null} />}
    >
      {!run ? (
        <CockpitEmptyState
          title="No workflow run yet"
          message="Run a deterministic daily scan to refresh provider health, prepare recovery context, score priority, generate digests, and create a brief."
        />
      ) : (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 bg-white/65 p-4 dark:border-slate-800 dark:bg-slate-950/40">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-[var(--strong)]">Run {shortIdentifier(run.id)}</p>
                <p className="mt-1 text-sm text-slate-500">Started {formatDateTime(run.started_at)} - Updated {formatRelativeTime(run.updated_at)}</p>
              </div>
              <CockpitBadge tone={toneForState(run.status)}>{commandCenterLabel(run.status)}</CockpitBadge>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{commandCenterText(run.summary, "Workflow status recorded.")}</p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <CockpitMetric label="Completed" value={formatInteger(completed)} tone="good" />
            <CockpitMetric label="Skipped" value={formatInteger(skipped)} tone="warning" />
            <CockpitMetric label="Failed" value={formatInteger(failed)} tone={failed ? "danger" : "neutral"} />
          </div>
          <div className="space-y-2">
            {steps.slice(0, 6).map((step) => (
              <div key={step.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-slate-200 bg-slate-50/70 p-3 dark:border-slate-800 dark:bg-slate-900/50">
                <div>
                  <p className="text-sm font-semibold text-[var(--strong)]">{humanizeLabel(step.step_key)}</p>
                  <p className="mt-1 text-xs text-slate-500">{commandCenterText(step.skipped_reason || step.error_message, "Step output recorded")}</p>
                </div>
                <CockpitBadge tone={toneForState(step.status)}>{commandCenterLabel(step.status)}</CockpitBadge>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <CockpitActionLink href={commandCenterHref("/brief", data.workspace?.id || null)} tone="info">Brief</CockpitActionLink>
            <CockpitActionLink href={commandCenterHref("/scanner", data.workspace?.id || null)} tone="good">Scanner</CockpitActionLink>
            <CockpitActionLink href={commandCenterHref("/triage", data.workspace?.id || null)} tone="warning">Triage</CockpitActionLink>
          </div>
        </div>
      )}
    </CockpitPanel>
  );
}

function NotificationsReviewPanel({ data }: { data: CommandCenterData }) {
  const blockers = data.latestProductReadiness?.blockers_json || [];
  const warnings = data.latestProductReadiness?.warnings_json || [];
  const workspaceId = data.workspace?.id || null;
  return (
    <CockpitPanel title="Notifications / Review Items" eyebrow="Inbox and readiness">
      <div className="grid grid-cols-2 gap-3">
        <CockpitMetric label="Unread inbox" value={formatInteger(data.notificationUnreadCount)} tone={data.notificationUnreadCount ? "info" : "neutral"} />
        <CockpitMetric label="Review items" value={formatInteger(data.notificationReviewCount)} tone={data.notificationReviewCount ? "warning" : "neutral"} />
        <CockpitMetric label="Blocked readiness" value={formatInteger(blockers.length)} tone={blockers.length ? "danger" : "good"} />
        <CockpitMetric label="Pending actions" value={formatInteger(data.summary.backendActionCount)} tone={data.summary.backendActionCount ? "warning" : "neutral"} />
      </div>
      <div className="mt-4 space-y-3">
        {[...blockers, ...warnings].slice(0, 4).map((item) => (
          <Link key={`${item.key}:${item.title}`} href={item.related_route || commandCenterHref("/readiness", workspaceId)} className="block rounded-2xl border border-slate-200 bg-slate-50/75 p-4 transition hover:bg-white dark:border-slate-800 dark:bg-slate-900/50">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <p className="font-semibold text-[var(--strong)]">{item.title}</p>
              <CockpitBadge tone={toneForState(item.status)}>{commandCenterLabel(item.status)}</CockpitBadge>
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{commandCenterText(item.summary, "Readiness context")}</p>
          </Link>
        ))}
        {blockers.length === 0 && warnings.length === 0 && (
          <CockpitEmptyState title="No blocked readiness" message="No readiness blockers or warnings were returned for this workspace." />
        )}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <CockpitActionLink href={commandCenterHref("/notifications", workspaceId)} tone="info">Open inbox</CockpitActionLink>
        <CockpitActionLink href={commandCenterHref("/readiness", workspaceId)} tone="warning">Open readiness</CockpitActionLink>
      </div>
    </CockpitPanel>
  );
}

function DailyIntelligenceMap({ data }: { data: CommandCenterData }) {
  return (
    <CockpitPanel title="Daily Intelligence Map" eyebrow="Navigation">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {data.navigationItems.slice(0, 8).map((item) => (
          <Link key={item.id} href={item.href} className="rounded-2xl border border-slate-200 bg-white/65 p-4 transition hover:-translate-y-0.5 hover:shadow-sm dark:border-slate-800 dark:bg-slate-950/35">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <p className="font-semibold text-[var(--strong)]">{item.label}</p>
              <CockpitBadge tone={item.tone}>Open</CockpitBadge>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.detail}</p>
          </Link>
        ))}
      </div>
    </CockpitPanel>
  );
}

function CommandCenterBackendState({ data }: { data: CommandCenterData }) {
  const visibleFailures = data.failures.filter((failure) => !failure.missing).slice(0, 4);
  if (!data.backendUnavailable && visibleFailures.length === 0) {
    return null;
  }
  return (
    <CockpitPanel title="Backend State" eyebrow="Availability">
      <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-4 dark:border-amber-900 dark:bg-amber-950/35">
        <div className="flex flex-wrap items-center gap-2">
          <CockpitBadge tone={data.backendUnavailable ? "danger" : "warning"}>
            {data.backendUnavailable ? "Backend unavailable" : "Partial backend response"}
          </CockpitBadge>
          <CockpitBadge tone="neutral">{data.apiBaseUrl}</CockpitBadge>
        </div>
        <p className="mt-3 text-sm leading-6 text-amber-900 dark:text-amber-100">
          Optional sections fail gracefully. The cockpit keeps available market intelligence visible and marks unavailable data explicitly.
        </p>
      </div>
      {visibleFailures.length > 0 && (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {visibleFailures.map((failure) => (
            <div key={`${failure.label}:${failure.status}:${failure.message}`} className="rounded-2xl border border-slate-200 bg-white/70 p-4 dark:border-slate-800 dark:bg-slate-950/35">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <p className="font-semibold text-[var(--strong)]">{failure.label}</p>
                <CockpitBadge tone={failure.status === 0 ? "danger" : "warning"}>{failure.status === 0 ? "Network" : failure.status}</CockpitBadge>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{commandCenterText(failure.message, "Backend context unavailable")}</p>
            </div>
          ))}
        </div>
      )}
    </CockpitPanel>
  );
}

function readinessLabel(data: CommandCenterData): { label: string; tone: CommandCenterTone } {
  const readiness = data.latestProductReadiness;
  if (!readiness) {
    return { label: "Readiness not available", tone: "neutral" };
  }
  return {
    label: commandCenterLabel(readiness.readiness_label),
    tone: toneForState(readiness.readiness_label),
  };
}

function providerPollingSummary(data: CommandCenterData): string {
  if (data.providerPollingRequests.length === 0) {
    return "No provider polling requests were returned. Use data onboarding for recovery preparation when needed.";
  }
  const byStatus = data.providerPollingRequests.reduce<Record<string, number>>((counts, request) => {
    counts[request.status] = (counts[request.status] || 0) + 1;
    return counts;
  }, {});
  return Object.entries(byStatus)
    .map(([status, count]) => `${formatInteger(count)} ${humanizeLabel(status)}`)
    .join(", ");
}

function toneForBias(value: string): CommandCenterTone {
  const normalized = value.toLowerCase();
  if (normalized.includes("bullish")) {
    return "good";
  }
  if (normalized.includes("bearish")) {
    return "danger";
  }
  if (normalized.includes("neutral") || normalized.includes("no directional")) {
    return "info";
  }
  return "neutral";
}
