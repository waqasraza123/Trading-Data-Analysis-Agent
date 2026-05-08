import { AppShell } from "@/components/layout/AppShell";
import { EmptyState } from "@/components/empty-states/empty-state";
import { JournalEntryDetail } from "@/components/journal/JournalEntryDetail";
import { AnimatedSection } from "@/components/ui/motion";
import { getJournalData } from "@/lib/api/journal";

type JournalEntryPageProps = {
  params: Promise<{ entryId: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
};

export default async function JournalEntryPage({ params, searchParams }: JournalEntryPageProps) {
  const routeParams = await params;
  const queryParams = await searchParams;
  const data = await getJournalData({ ...queryParams, entryId: routeParams.entryId });

  return (
    <AppShell appName={data.appName} workspaceId={data.workspace?.id} workspaceName={data.workspace?.name}>
      <AnimatedSection as="section" className="space-y-6">
        {data.selectedEntry ? (
          <JournalEntryDetail data={data} selectedEntry={data.selectedEntry} />
        ) : (
          <EmptyState
            title="Journal entry unavailable"
            message="The backend did not return this journal entry, or the journal endpoint is unavailable."
          />
        )}
      </AnimatedSection>
    </AppShell>
  );
}
