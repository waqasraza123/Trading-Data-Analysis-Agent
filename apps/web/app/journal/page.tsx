import { AppShell } from "@/components/layout/AppShell";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { EmptyState } from "@/components/empty-states/empty-state";
import { JournalEntryDetail } from "@/components/journal/JournalEntryDetail";
import { JournalEntryForm } from "@/components/journal/JournalEntryForm";
import { JournalFilters } from "@/components/journal/JournalFilters";
import { JournalEntryList } from "@/components/journal/JournalEntryList";
import {
  ReviewMetricGrid,
  ReviewSurfaceHero,
  ReviewSurfaceMetric,
} from "@/components/review-surfaces/ReviewSurface";
import { AnimatedListItem, AnimatedSection, motionRevealDensityStyle } from "@/lib/ui/motion";
import { getJournalData } from "@/lib/api/journal";

type JournalPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function JournalPage({ searchParams }: JournalPageProps) {
  const params = await searchParams;
  const data = await getJournalData(params);

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        <AnimatedListItem as="section" style={motionRevealDensityStyle(0, "comfortable")}>
          <ReviewSurfaceHero
            eyebrow="Daily journal"
            title="Reflection notes"
            description="Capture observational notes, linked setup context, and outcome reflection for the daily review loop. The surface stays non-advisory and excludes account-result fields."
            actions={
              <>
                <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
                <WorkflowLinks
                  workspaceId={data.workspace?.id}
                  targets={["commandCenter", "review", "triage", "brief", "preferences"]}
                />
              </>
            }
          />
        </AnimatedListItem>
        {!data.workspace ? (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(1, "comfortable")}>
            <EmptyState
              title="No workspace available"
              message="Seed or create a workspace in the API before journal entries can load."
            />
          </AnimatedListItem>
        ) : data.failures.some((failure) => failure.label === "Journal entries" && failure.missing) ? (
          <AnimatedListItem as="section" style={motionRevealDensityStyle(2, "comfortable")}>
            <EmptyState
              title="Journal API unavailable"
              message="The backend did not expose journal entries for this environment. Outcome review can still show available deterministic artifacts."
            />
          </AnimatedListItem>
        ) : (
          <>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(3, "regular")}>
              <ReviewMetricGrid>
                <ReviewSurfaceMetric label="Visible notes" value={data.entries.length} detail="After current filters" tone="info" />
                <ReviewSurfaceMetric label="Stored notes" value={data.unfilteredEntryCount} detail="Workspace journal entries" />
                <ReviewSurfaceMetric label="Linked outcomes" value={data.outcomes.length} detail="Loaded for focused signal context" tone="good" />
                <ReviewSurfaceMetric label="Workspace" value={data.workspace.name} detail="Current review scope" />
              </ReviewMetricGrid>
            </AnimatedListItem>
            <AnimatedListItem as="section" style={motionRevealDensityStyle(4, "compact")}>
              <JournalFilters data={data} />
            </AnimatedListItem>
            <div className="grid gap-5 xl:grid-cols-[minmax(380px,460px)_minmax(0,1fr)]">
              <AnimatedListItem as="section" style={motionRevealDensityStyle(5, "compact")}>
                <div className="space-y-5">
                  <JournalEntryForm data={data} />
                  <JournalEntryList
                    entries={data.entries}
                    workspaceId={data.workspace.id}
                    contexts={data.entryContexts}
                    unfilteredEntryCount={data.unfilteredEntryCount}
                  />
                </div>
              </AnimatedListItem>
              <AnimatedListItem as="section" style={motionRevealDensityStyle(6, "compact")}>
                {data.selectedEntry ? (
                  <JournalEntryDetail data={data} selectedEntry={data.selectedEntry} />
                ) : (
                  <EmptyState
                    title="Select or create a note"
                    message="Open a journal entry to review it against observed outcomes when linked outcome data is available."
                  />
                )}
              </AnimatedListItem>
            </div>
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
