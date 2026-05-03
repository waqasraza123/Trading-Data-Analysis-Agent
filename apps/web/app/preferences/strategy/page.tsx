import { PreferenceProfileEmptyState } from "@/components/preferences/PreferenceProfileEmptyState";
import { PreferenceProfileFilters } from "@/components/preferences/PreferenceProfileFilters";
import { PreferenceProfileForm } from "@/components/preferences/PreferenceProfileForm";
import { PreferenceProfileList } from "@/components/preferences/PreferenceProfileList";
import { PreferenceProfileSummary } from "@/components/preferences/PreferenceProfileSummary";
import { Badge } from "@/components/status/badge";
import { AppShell } from "@/components/layout/app-shell";
import { getPreferenceProfilesPageData } from "@/lib/api/preferenceProfiles";
import { formatDateTime } from "@/lib/formatting/dates";

type StrategyPreferencesPageProps = {
  searchParams: Promise<{
    workspaceId?: string;
    profileId?: string;
  }>;
};

export default async function StrategyPreferencesPage({
  searchParams,
}: StrategyPreferencesPageProps) {
  const params = await searchParams;
  const data = await getPreferenceProfilesPageData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <section className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-slate-500">Personal review preferences</p>
            <h2 className="mt-1 text-3xl font-semibold text-[var(--strong)]">
              Strategy preference profiles
            </h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
              Define the markets, sessions, symbols, patterns, confidence thresholds, and data
              freshness requirements that should shape review workflows.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge value={data.workspace?.name || "No workspace"} tone="info" />
              <Badge value={`Updated ${formatDateTime(data.lastUpdatedAt)}`} />
            </div>
          </div>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm text-slate-500">
            Filters only. No execution workflow.
          </div>
        </section>
        {!data.workspace ? (
          <PreferenceProfileEmptyState
            title="No workspace available"
            message="Seed or create a workspace before preference profiles can be configured."
          />
        ) : (
          <>
            <PreferenceProfileSummary data={data} />
            <PreferenceProfileFilters data={data} />
            <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_460px]">
              <PreferenceProfileList data={data} />
              <PreferenceProfileForm data={data} />
            </div>
            {data.filterContext && (
              <section className="surface rounded-lg p-5">
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Safety boundaries
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {data.filterContext.safety_boundaries.map((boundary) => (
                    <Badge key={boundary} value={boundary} tone="info" />
                  ))}
                </div>
              </section>
            )}
            {data.failures.length > 0 && (
              <section className="surface rounded-lg p-5">
                <p className="text-xs font-semibold uppercase text-slate-500">API status</p>
                <div className="mt-3 space-y-2">
                  {data.failures.map((failure) => (
                    <p key={`${failure.label}:${failure.status}`} className="text-sm text-slate-600 dark:text-slate-300">
                      {failure.label}: {failure.message}
                    </p>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
