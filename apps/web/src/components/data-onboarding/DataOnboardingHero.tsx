import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Badge } from "@/components/status/badge";
import { formatDateTime } from "@/lib/formatting/dates";
import type { OnboardingInitialData, OnboardingSelection } from "@/lib/data-onboarding/types";

type DataOnboardingHeroProps = {
  initialData: OnboardingInitialData;
  selection: OnboardingSelection;
};

export function DataOnboardingHero({ initialData, selection }: DataOnboardingHeroProps) {
  const configuredCredentials = initialData.providerCredentialRefs.filter(
    (credential) => credential.secret_ref_configured && credential.status !== "revoked",
  ).length;
  const degradedProviders =
    (initialData.providerHealthSummary?.degraded_count || 0) +
    (initialData.providerHealthSummary?.failing_count || 0);
  const missingCandles =
    initialData.providerHealthSummary?.missing_candle_count ??
    initialData.providerHealthSnapshots.reduce(
      (count, snapshot) => count + snapshot.missing_candle_count,
      0,
    );
  const readinessLabel = missingCandles > 0
    ? "Blocked by missing candles"
    : degradedProviders > 0
      ? "Degraded"
      : initialData.providerHealthSnapshots.length > 0
        ? "Ready for deterministic analysis"
        : "Freshness check needed";

  return (
    <section className="overflow-hidden rounded-lg border border-[var(--line)] bg-[var(--panel)] shadow-[var(--shadow-panel)]">
      <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_340px]">
        <div className="p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-2">
            <Badge value={initialData.workspace?.name || "No workspace"} tone={initialData.workspace ? "info" : "warning"} />
            <Badge value={readinessLabel} tone={readinessLabel === "Ready for deterministic analysis" ? "good" : readinessLabel === "Freshness check needed" ? "warning" : "danger"} />
          </div>
          <div className="mt-5 max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Data onboarding
            </p>
            <h1 className="mt-2 text-3xl font-semibold text-[var(--strong)] sm:text-4xl">
              Guided source readiness for deterministic analysis
            </h1>
            <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
              Configure sources, verify server-side credential references, check final-candle
              freshness, detect missing candles, and prepare recovery plans without hidden external
              calls.
            </p>
          </div>
          <div className="mt-6">
            <WorkflowLinks
              workspaceId={selection.workspaceId}
              targets={["commandCenter", "scanner", "readiness", "quality", "triage", "journal"]}
            />
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <HeroMetric label="Sources" value={String(initialData.dataSources.length)} detail="Workspace data inputs" />
            <HeroMetric label="Credentials" value={String(configuredCredentials)} detail="Configured references" />
            <HeroMetric label="Provider health" value={String(initialData.providerHealthSnapshots.length)} detail={`${degradedProviders} degraded/failing`} />
            <HeroMetric label="Missing candles" value={String(missingCandles)} detail="Provider health snapshots" />
            <HeroMetric label="Last loaded" value={formatDateTime(initialData.lastUpdatedAt)} detail="Refresh reloads backend state" />
          </div>
        </div>
        <aside className="border-t border-[var(--line)] bg-[var(--panel-muted)] p-6 xl:border-l xl:border-t-0">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Safety boundary
          </p>
          <div className="mt-4 grid gap-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
            <p className="rounded-md border border-[var(--line)] bg-[var(--panel)] p-3">
              Recovery preparation creates metadata only unless backend settings explicitly allow
              request creation.
            </p>
            <p className="rounded-md border border-[var(--line)] bg-[var(--panel)] p-3">
              Raw provider secrets are never shown in the browser.
            </p>
            <p className="rounded-md border border-[var(--line)] bg-[var(--panel)] p-3">
              This workflow does not include broker execution or financial advice.
            </p>
          </div>
        </aside>
      </div>
    </section>
  );
}

function HeroMetric({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--surface)] p-4">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 truncate text-2xl font-semibold text-[var(--strong)]">{value}</p>
      <p className="mt-1 text-xs leading-5 text-slate-500">{detail}</p>
    </div>
  );
}
