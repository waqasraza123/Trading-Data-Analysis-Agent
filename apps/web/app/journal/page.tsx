import { AppShell } from "@/components/layout/app-shell";
import { WorkflowLinks } from "@/components/layout/workflow-links";
import { Metric } from "@/components/ui/Metric";
import { PageHeader } from "@/components/ui/PageHeader";
import { EmptyState } from "@/components/empty-states/empty-state";
import { JournalEntryDetail } from "@/components/journal/JournalEntryDetail";
import { JournalEntryForm } from "@/components/journal/JournalEntryForm";
import { JournalEntryList } from "@/components/journal/JournalEntryList";
import { getJournalData } from "@/lib/api/journal";

type JournalPageProps = {
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function JournalPage({ searchParams }: JournalPageProps) {
  const params = await searchParams;
  const data = await getJournalData(params);

  return (
    <AppShell appName={data.appName}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Journal feedback"
          title="Review notes"
          description="Capture observations, bias, and outcome reflection for deterministic setup review. This page avoids broker execution, account metrics, and financial-advice language."
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
          <div className="grid gap-5 xl:grid-cols-[minmax(360px,440px)_minmax(0,1fr)]">
            <div className="space-y-5">
              <JournalEntryForm data={data} />
              <JournalEntryList entries={data.entries} workspaceId={data.workspace.id} />
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
        )}
      </div>
    </AppShell>
  );
}
