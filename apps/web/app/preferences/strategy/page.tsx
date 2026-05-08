import { PreferenceProfileEmptyState } from "@/components/preferences/PreferenceProfileEmptyState";
import { PreferenceProfileFilters } from "@/components/preferences/PreferenceProfileFilters";
import { PreferenceProfileForm } from "@/components/preferences/PreferenceProfileForm";
import { PreferenceProfileList } from "@/components/preferences/PreferenceProfileList";
import { PreferenceProfileSummary } from "@/components/preferences/PreferenceProfileSummary";
import { Badge } from "@/components/status/badge";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
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
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <PageHeader
            eyebrow="Personal review preferences"
            title="Strategy preference profiles"
            description="Define the markets, sessions, symbols, patterns, confidence thresholds, and data freshness requirements that should shape review workflows."
            meta={
              <>
                <Badge value={data.workspace?.name || "No workspace"} tone="info" />
                <Badge value={`Updated ${formatDateTime(data.lastUpdatedAt)}`} />
              </>
            }
            actions={<Badge value="Filters only" tone="info" />}
          />
        </AnimatedListItem>
        {!data.workspace ? (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <PreferenceProfileEmptyState
              title="No workspace available"
              message="Seed or create a workspace before preference profiles can be configured."
            />
          </AnimatedListItem>
        ) : (
          <>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "compact")}>
              <PreferenceProfileSummary data={data} />
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "compact")}>
              <PreferenceProfileFilters data={data} />
            </AnimatedListItem>
            <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_460px]">
              <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
                <PreferenceProfileList data={data} />
              </AnimatedListItem>
              <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
                <PreferenceProfileForm data={data} />
              </AnimatedListItem>
            </div>
            {data.filterContext && (
              <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "regular")}>
                <Section>
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    Safety boundaries
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {data.filterContext.safety_boundaries.map((boundary) => (
                      <Badge key={boundary} value={boundary} tone="info" />
                    ))}
                  </div>
                </Section>
              </AnimatedListItem>
            )}
            {data.failures.length > 0 && (
              <AnimatedListItem as="section" style={motionRevealDensityStyle(7, "regular")}>
                <Section>
                  <p className="text-xs font-semibold uppercase text-slate-500">API status</p>
                  <div className="mt-3 space-y-2">
                    {data.failures.map((failure) => (
                      <p key={`${failure.label}:${failure.status}`} className="text-sm text-slate-600 dark:text-slate-300">
                        {failure.label}: {failure.message}
                      </p>
                    ))}
                  </div>
                </Section>
              </AnimatedListItem>
            )}
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
