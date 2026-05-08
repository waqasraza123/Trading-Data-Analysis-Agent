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
import { AnimatedSection } from "@/components/ui/motion";
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
        <ReviewSurfaceHero
          eyebrow="Daily journal"
          title="Reflection notes"
          description="Capture observational notes, linked setup context, and outcome reflection for the daily review loop. The surface stays non-advisory and excludes account-result fields."
          actions={
            <>
            <Metric label="Workspace" value={data.workspace?.name || "Not selected"} />
            <WorkflowLinks workspaceId={data.workspace?.id} targets={["commandCenter", "review", "triage", "brief", "preferences"]} />
          </>
          }
        />
        {!data.workspace ? (
          <EmptyState
            title="No workspace available"
            message="Seed or create a workspace in the API before journal entries can load."
          />
        ) : data.failures.some((failure) => failure.label === "Journal entries" && failure.missing) ? (
          <EmptyState
            title="Journal API unavailable"
            message="The backend did not expose journal entries for this environment. Outcome review can still show available deterministic artifacts."
          />
        ) : (
          <>
            <ReviewMetricGrid>
              <ReviewSurfaceMetric label="Visible notes" value={data.entries.length} detail="After current filters" tone="info" />
              <ReviewSurfaceMetric label="Stored notes" value={data.unfilteredEntryCount} detail="Workspace journal entries" />
              <ReviewSurfaceMetric label="Linked outcomes" value={data.outcomes.length} detail="Loaded for focused signal context" tone="good" />
              <ReviewSurfaceMetric label="Workspace" value={data.workspace.name} detail="Current review scope" />
            </ReviewMetricGrid>
            <JournalFilters data={data} />
            <div className="grid gap-5 xl:grid-cols-[minmax(380px,460px)_minmax(0,1fr)]">
              <div className="space-y-5">
                <JournalEntryForm data={data} />
                <JournalEntryList
                  entries={data.entries}
                  workspaceId={data.workspace.id}
                  contexts={data.entryContexts}
                  unfilteredEntryCount={data.unfilteredEntryCount}
                />
              </div>
              {data.selectedEntry ? (
                <JournalEntryDetail data={data} selectedEntry={data.selectedEntry} />
              ) : (
                <EmptyState
                  title="Select or create a note"
                  message="Open a journal entry to review it against observed outcomes when linked outcome data is available."
                />
              )}
            </div>
          </>
        )}
      </AnimatedSection>
    </AppShell>
  );
}
